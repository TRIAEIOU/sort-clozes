import re
from anki import notes, collection
from aqt import mw, qt, operations, browser, gui_hooks
from anki.consts import *
from .version import *

TITLE = "Sort clozes"
NVER = "1.0.0"

#########################################################################
def sort_notes(parent: qt.QMainWindow, nids: list[notes.NoteId]):
    """Sort clozes on notes in background op, checks for non-cloze notes"""

    def sort(col: collection.Collection, nids: list[notes.NoteId]):
        changes = collection.OpChanges()
        notes = []
        cards = []
        for nid in nids:
            note = col.get_note(nid)
            if note.note_type().get('type', MODEL_STD) != MODEL_CLOZE: continue
            #print(":found note " + str(nid))

            note_cards = {}
            for card in note.cards():
                # db is 0-based, notes 1-based
                note_cards[str(card.ord + 1)] = {'card': card, 'ord': -1}

            i = 0
            def substitute(match):
                nonlocal i, cards
                # Multicloze cards should only be added once, after that reuse same ord
                if card := note_cards[match.group(1)]['card']:
                    card.ord = i # db is 0-based
                    i += 1 # notes are 1-based
                    #print(rf":      appending card {str(card.id)}")
                    cards.append(card)
                    note_cards[match.group(1)] = {'card': None, 'ord': i}
                    ord = i
                else: ord = note_cards[match.group(1)]['ord']

                #print(rf":    returning '{{{{c{ord}::'")
                return rf'{{{{c{ord}::'

            for fld in note.keys():
                note[fld] = re.sub(r'{{c(\d+)::', substitute, note[fld])


            #print(":  appending note " + str(note.id))
            notes.append(note)

        #print(":updating cards: " + str(", ".join([str(t.id) for t in cards])))
        col.update_cards(cards)
        #print(":updating notes: " + str(", ".join([str(t.id) for t in notes])))
        col.update_notes(notes)
        return changes

    def _success(changes):
        pass

    # Create a root backup
    mw.col.create_backup(
        backup_folder=mw.pm.backupFolder(),
        force=True,
        wait_for_completion=True,
    )
    bgop = operations.CollectionOp(
      parent=parent,
      op=lambda col: sort(col, nids)
    )
    bgop.run_in_background()
    bgop.success(success=_success)


#########################################################################
def sort_table(browser: browser.Browser, menu: qt.QMenu):
    """Add menu entry on browser table context"""
    if (len(browser.selected_notes()) > 0):
        action = qt.QAction(TITLE, menu)
        action.triggered.connect(
          lambda: sort_notes(browser, browser.table.get_selected_note_ids())
        )
        menu.addAction(action)
    return menu


#########################################################################
def sort_sidebar(sidebar: browser.SidebarTreeView, menu: qt.QMenu,
                 item: browser.SidebarItem, index: qt.QModelIndex):
    """Add menu entry on browser sidebar context"""
    def exe():
        nids = {}
        for cid in sidebar.col.decks.cids(item.id, True):
            nid = sidebar.col.get_card(cid).nid
            nids[nid] = True
        sort_notes(sidebar.browser, list(nids.keys()))

    if item.item_type == browser.SidebarItemType.DECK:
        action = qt.QAction(TITLE, menu)
        action.triggered.connect(exe)
        menu.addAction(action)
    return menu

#########################################################################
def sort_toolbar(win):
    """Add menu entry to main windows toolbar"""
    def exe():
        nids = {}
        for cid in win.col.decks.cids(win.col.decks.get_current_id(), True):
            nids[win.col.get_card(cid).nid] = True
        sort_notes(win, list(nids))

    action = qt.QAction(TITLE, win)
    action.triggered.connect(exe)
    mw.form.menuTools.addAction(action)

# Main ##################################################################
if strvercmp(NVER, get_version()) > 0: set_version(NVER)

sort_toolbar(mw)
gui_hooks.browser_will_show_context_menu.append(sort_table)
gui_hooks.browser_sidebar_will_show_context_menu.append(sort_sidebar)
