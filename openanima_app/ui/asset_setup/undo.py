import copy


def snapshot(dialog):
    return {
        "layers": copy.deepcopy(dialog.layers),
        "selected_layer_id": dialog.selected_layer_id,
        "next_layer_id": dialog.next_layer_id,
    }


def restore_snapshot(dialog, snapshot_data):
    dialog._applying_history = True
    dialog.layers = copy.deepcopy(snapshot_data["layers"])
    dialog.selected_layer_id = snapshot_data.get("selected_layer_id")
    dialog.next_layer_id = snapshot_data.get("next_layer_id", dialog.next_layer_id)
    dialog.selected_layer_index = dialog.index_for_layer_id(dialog.selected_layer_id)
    dialog.sync_layer_list()
    dialog.select_layer(dialog.selected_layer_index)
    dialog._applying_history = False
    dialog.mark_dirty()


def push_undo_state(dialog, description="", coalesce_key=None):
    if dialog._loading or dialog._applying_history:
        return
    if coalesce_key and dialog._coalesce_key == coalesce_key:
        return
    dialog.undo_stack.append(dialog.snapshot())
    if len(dialog.undo_stack) > dialog.max_history:
        dialog.undo_stack.pop(0)
    dialog.redo_stack.clear()
    dialog._coalesce_key = coalesce_key


def end_coalesce(dialog):
    dialog._coalesce_key = None


def undo(dialog):
    if not dialog.undo_stack:
        return
    dialog.redo_stack.append(dialog.snapshot())
    dialog.restore_snapshot(dialog.undo_stack.pop())


def redo(dialog):
    if not dialog.redo_stack:
        return
    dialog.undo_stack.append(dialog.snapshot())
    dialog.restore_snapshot(dialog.redo_stack.pop())
