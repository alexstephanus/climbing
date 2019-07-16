"""Contains the results of an individual session
"""

from collections import namedtuple
import datetime
import filecmp
import json
import logging
import os
import pprint
from typing import Dict, List, Optional, Tuple, Union

from bson import json_util

_STORAGE_FILE_LOC = 'sessions/current.json'
_OLD_FILE_FORMAT = 'sessions/old/result_{date}.json'
_DATE_FORMAT = '%Y-%m-%d'

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

Route = namedtuple('Route', ['index', 'grade', 'type', 'perf'])


def curr_date_as_datetime() -> datetime.datetime:
    today = datetime.date.today()
    return datetime.datetime(today.year, today.month, today.day)

def create_route(idx: int, rec: Union[Tuple[str, int], Dict]) -> Route:
    """Instantiates a route from a tuple
    """
    if isinstance(rec, dict):
        return Route(idx, rec['grade'], rec['type'], rec['perf'])
    elif isinstance(rec, tuple):
        return Route(idx, rec[0], rec[1], rec[2])
    else:
        raise NotImplementedError(f"Gotta be a tuple or dict, you gave us a {type(rec)}")


class Session:

    def __init__(self, routes: List[Union[Tuple[str, int], Dict]], date: Optional[datetime.date]):
        self.date = date or curr_date_as_datetime()
        self.routes: List[Route] = [create_route(idx, route) for idx, route in enumerate(routes)]

    def to_json(self):
        routes = [{
            'idx': route.index,
            'grade': route.grade,
            'type': route.type,
            'perf': route.perf,
        } for route in self.routes]
        return json.dumps({
            'date': self.date,
            'routes': routes,
        }, default=json_util.default)

    @classmethod
    def from_json(cls, json_str) -> 'Session':
        return cls(**json_util.loads(json_str))

    @classmethod
    def from_csv_str(cls, csv_str: str, date: Optional[datetime.date]) -> 'Session':
        routes = []
        for route_line in csv_str.splitlines():
            parts = route_line.split(',')
            routes.append((parts[0].strip(), parts[1].strip(), int(parts[2].strip())))

        return cls(routes, date)

    def __repr__(self) -> str:
        route_dicts = [route._asdict() for route in self.routes]
        ret = pprint.pformat(f'Date: {self.date}, routes: \n')
        ret += '\n'.join([pprint.pformat({k:v for k, v in route.items()}) for route in route_dicts])
        return ret


class TrainingLog:

    def __init__(self, sessions: List[Session]):
        self.sessions = sessions

    @classmethod
    def load(cls) -> 'TrainingLog':
        _LOGGER.info('Loading TrainingLog from file')
        if not os.path.exists(_STORAGE_FILE_LOC):
            return TrainingLog([])
        with open(_STORAGE_FILE_LOC, 'r') as fp:
            sessions = [Session.from_json(line) for line in fp.readlines()]
        return TrainingLog(sessions)

    def update_file(self, file: str) -> None:
        if os.path.exists(file):
            os.remove(file)
        with open(file, 'w') as fp:
            fp.write(self.dump_jsons())

    def write(self) -> None:
        latest_session = sorted(self.sessions, key=lambda session: session.date)[-1]
        _LOGGER.info(f'type: {type(latest_session)}')
        latest_date = latest_session.date
        self.update_file(_OLD_FILE_FORMAT.format(date=latest_date.strftime(_DATE_FORMAT)))
        self.update_file(_STORAGE_FILE_LOC)

    @classmethod
    def update_from_csv_str(cls, csv_str: str, date: Optional[datetime.date] = None) -> None:
        _LOGGER.info("Loading")
        log = TrainingLog.load()
        new_session = Session.from_csv_str(csv_str, date)
        if len(log.sessions) != 0:
            if new_session == log.sessions[-1]:
                _LOGGER.info("Skipping write, looks like a dupe last entry")
        _LOGGER.info("Updating and writing")
        log.sessions.append(new_session)
        log.write()

    def dump_jsons(self) -> str:
        return '\n'.join([sesh.to_json() for sesh in self.sessions])


######################### Perf Ratings #########################
#
# 5: Finished clean
# 4: Finished w/ takes
# 3: Finished w >1 take or within 3 clips
# 2: >4 clips but no finish
# 1: 3-4 clips
# 0: 0-2 clips
#
################################################################

_DATE = datetime.datetime(2019, 7, 14)

_CSV_STR = """\
5.10a, lead, 5
5.10c, lead, 5
5.11a, lead, 5
5.12a, lead, 2
5.12a, lead, 1
5.11d, lead, 3
5.11d, TR, 5
5.11d, lead, 0\
"""

if __name__ == '__main__':
    _LOGGER.info("Here")
    TrainingLog.update_from_csv_str(_CSV_STR, _DATE)
    _LOGGER.info("Done")
