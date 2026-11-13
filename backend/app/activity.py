"""Public execution updates, never raw model reasoning or provider prose."""


async def report(callback, event_id, label, status='running'):
    if callback is not None:
        await callback({'type': 'activity', 'id': event_id, 'label': label, 'status': status})
