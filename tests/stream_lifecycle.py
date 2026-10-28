"""Closed, content-free lifecycle checks shared by pure harness reducers."""


def faulty_metadata(event):
    """Absence is benign; present failure/completeness fields must be unambiguous."""
    if event.get('error') is not None and event.get('error') != '':
        return True
    for field in ('errors', 'permission_denials'):
        value = event.get(field)
        if value is not None and (type(value) is not list or value):
            return True
    deferred = event.get('deferred_tool_use')
    if deferred is not None and deferred is not False:
        return True
    return False


def benign_hook(event, expected_session, label):
    """Recognize successful native hooks, never reset/compaction/future events."""
    if event.get('subtype') not in ('hook_started', 'hook_response'):
        return False
    if event.get('session_id') != expected_session or faulty_metadata(event):
        return False
    for field in ('hook_id', 'hook_name', 'hook_event'):
        value = event.get(field)
        if type(value) is not str or not label.fullmatch(value):
            return False
    outcome, code = event.get('outcome'), event.get('exit_code')
    if code is not None and (type(code) is not int or code != 0):
        return False
    if event['subtype'] == 'hook_response':
        return outcome == 'success' and code == 0
    return outcome in (None, 'success')
