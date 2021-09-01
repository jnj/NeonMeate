
def format_seconds(secs):
    m, s = divmod(secs, 60)

    if m >= 60:
        h, m = divmod(m, 60)
        return f'{h:02}:{m:02}:{s:02}'

    return f'{m:02}:{s:02}'


def format_elapsed_time(elapsed_seconds, total_seconds):
    n = format_seconds(elapsed_seconds)
    d = format_seconds(total_seconds)
    return f'{n} / {d}'