import re, anki, aqt
from anki.consts import *

TITLE = "Sort clozes"

#########################################################################
def sort_notes(parent: aqt.qt.QMainWindow, nids: list[anki.notes.NoteId]):
    """Sort clozes on notes in background op, checks for non-cloze notes"""

    def sort(col: anki.collection.Collection, nids: list[anki.notes.NoteId]):
        changes = anki.collection.OpChanges()
        notes = []
        cards = []
        for nid in nids:
            note = col.get_note(nid)
            if note.note_type().get('type', MODEL_STD) != MODEL_CLOZE: continue

            note_cards = {str(card.ord + 1): card for card in note.cards()}
            i = 0

            def substitute(match):
                nonlocal i, cards
                i += 1
                card = note_cards[match.group(1)]
                card.ord = i - 1
                cards.append(card)
                return rf'{{{{c{i}::'

            for fld in note.keys():
                note[fld] = re.sub(r'{{c(\d+)::', substitute, note[fld])

            notes.append(note)

        col.update_cards(cards)
        col.update_notes(notes)
        return changes

    def _success(changes):
        pass

    # Create a root backup
    aqt.mw.col.create_backup(
        backup_folder=aqt.mw.pm.backupFolder(),
        force=True,
        wait_for_completion=True,
    )
    bgop = aqt.operations.CollectionOp(
      parent=parent,
      op=lambda col: sort(col, nids)
    )
    bgop.run_in_background()
    bgop.success(success=_success)


#########################################################################
def sort_table(browser: aqt.browser.Browser, menu: aqt.qt.QMenu):
    """Add menu entry on browser table context"""
    if (len(browser.selected_notes()) > 0):
        action = aqt.qt.QAction(TITLE, menu)
        action.triggered.connect(
          lambda: sort_notes(browser, browser.table.get_selected_note_ids())
        )
        menu.addAction(action)
    return menu


#########################################################################
def sort_sidebar(sidebar: aqt.browser.SidebarTreeView, menu: aqt.qt.QMenu,
                 item: aqt.browser.SidebarItem, index: aqt.qt.QModelIndex):
    """Add menu entry on browser sidebar context"""

    if item.item_type == aqt.browser.SidebarItemType.DECK:
        action = aqt.qt.QAction(TITLE, menu)
        action.triggered.connect(lambda: sort_notes(
          sidebar.browser,
          list(dict([
            sidebar.col.get_card(cid).nid
            for cid in sidebar.col.decks.cids(item.id, True)
          ]))
        ))
        menu.addAction(action)
    return menu

# Main ##################################################################
action = aqt.qt.QAction(TITLE, aqt.mw)
action.triggered.connect(lambda: sort_notes(
  aqt.mw,
  aqt.mw.col.decks.cids(aqt.mw.col.decks.get_current_id(), True)
))
aqt.mw.form.menuTools.addAction(action)

aqt.gui_hooks.browser_will_show_context_menu.append(sort_table)
aqt.gui_hooks.browser_sidebar_will_show_context_menu.append(sort_sidebar)
