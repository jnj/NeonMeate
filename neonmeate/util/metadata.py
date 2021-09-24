import logging

import dateparser


def parse_date(date: str):
    try:
        return dateparser.parse(date).year
    except ValueError as e:
        logging.debug(e)


def parse_disc(song: dict) -> int:
    disc = song.get('disc', 1)
    try:
        if isinstance(disc, (list, set)):
            return int(disc[0])
        else:
            return int(disc)
    except ValueError:
        logging.warning(f"Failed to parse disc {disc}")
