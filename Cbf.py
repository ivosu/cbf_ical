import xml.etree.ElementTree as ElementTree
import json
import urllib.request
from typing import Tuple, Dict, List, Optional, Self
from datetime import datetime
import pytz
import sys

cbf_api_endpoint = "https://www.cbf.cz/xml/"


class Referee:
    def __init__(self, ref_id: int, first_name: str, last_name: str):
        self.id = ref_id
        self.first_name = first_name
        self.last_name = last_name


class Team:
    def __init__(self, team_id: int, team_name: str, abbr: str):
        self.id = team_id
        self.name = team_name
        self.abbr = abbr


class Match:
    class Result:
        def __init__(self, pts: Tuple[int, int], score: Tuple[int, int],
                     partials: Dict[str, Tuple[int, int]], url_live: str):
            self.pts = pts
            self.score = score
            self.partials = partials
            self.url_live = url_live

    class Location:
        def __init__(self, place: str, city: str,
                     coordinates: Optional[Tuple[float, float]] = None):
            self.place = place
            self.city = city
            self.coordinates = coordinates

    # possible addition - round
    def __init__(self, id: int, home_team: Team, visiting_team: Team,
                 start: Optional[datetime], location: Location,
                 refs: List[Referee], supervisor: Optional[Referee],
                 result: Optional[Result]):
        self.id = id
        self.home_team = home_team
        self.visiting_team = visiting_team
        self.start = start
        self.location = location
        self.refs = refs
        self.supervisor = supervisor
        self.result = result


class Schedule:
    def __init__(self, phase_id: int, matches: List[Match]):
        self.phase_id = phase_id
        self.matches = matches


class TeamStanding:
    def __init__(self, team_id: int, team_name: str, abbr: str, position: int,
                 games_played: int, games_won: int, games_lost: int,
                 points_scored: int, points_allowed: int, points: str):
        self.id = team_id
        self.name = team_name
        self.abbr = abbr
        self.position = position
        self.games_played = games_played
        self.games_won = games_won
        self.games_lost = games_lost
        self.points_scored = points_scored
        self.points_allowed = points_allowed
        self.points = points


class Standings:
    def __init__(self, phase_id: int, team_standings: List[TeamStanding]):
        self.phase_id = phase_id
        self.team_standings = team_standings


class Phase:
    # possible additions - type, offset
    def __init__(self, phase_id: int, phase_name: str,
                 schedule: Schedule, standings: Standings):
        self.id = phase_id
        self.name = phase_name
        self.schedule = schedule
        self.standings = standings


class Division:
    """
    # possibly usable in future
    from enum import Enum, auto

    class Flags(Enum):
        public = auto()
        finished = auto()
        players = auto()
        results = auto()
        stats = auto()
        events = auto()
        refeval = auto()
        clubeval = auto()
        gplayers = auto()
        sups = auto()
    """

    def __init__(self, division_id: int, division_name: str,
                 phases: List[Phase]):
        self.id = division_id
        self.name = division_name
        self.phases = phases


class Season:
    def __init__(self, year: int, divisions: List[Division]):
        self.year = year
        self.divisions = divisions


areas: Dict[str, int] = {
    'ČBF (celostátní)': 0,
    'Praha': 1,
    'Střední Čechy': 2,
    'Jižní Čechy': 3,
    'Severní Čechy': 5,
    'Východní Čechy': 6,
    'Jižní Morava': 7,
    'Moravskoslezský': 8,
    'Olomoucký': 12,
    'Karlovarský': 13,
    'Plzeňský': 14,
}


class SeasonDescription:
    def __init__(self, id: int, name: str, short_name: str, current: bool):
        self.id = id
        self.name = name
        self.short_name = short_name
        self.current = current

    @classmethod
    def from_xml(cls, xml: ElementTree.Element) -> Self:
        return cls(int(xml.findtext('IDseason', '')),
                   xml.findtext('name', ''),
                   xml.findtext('short_name', ''),
                   bool(int(xml.findtext('current', ''))))


class CbfApiFetcher_v1:
    def __init__(self, api_url: str):
        self.api_url = api_url

    def fetch_season(self, year: int) -> Optional[Season]:
        request_url = self.api_url + 'divs.php?s=' + str(year)
        with urllib.request.urlopen(request_url) as response:
            raw_xml = response.read()
        try:
            xml = ElementTree.fromstring(raw_xml)
            return self.parse_season(xml, year)
        except ElementTree.ParseError:
            return None

    def fetch_schedule(self, phase_id: int) -> Optional[Schedule]:
        request_url = self.api_url + 'sched.php?p=' + str(phase_id)
        with urllib.request.urlopen(request_url) as response:
            raw_xml = response.read()
        try:
            xml = ElementTree.fromstring(raw_xml)
            return self.parse_schedule(xml, phase_id)
        except ElementTree.ParseError:
            return None

    def fetch_standings(self, phase_id: int) -> Optional[Standings]:
        request_url = self.api_url + 'table.php?p=' + str(phase_id)
        with urllib.request.urlopen(request_url) as response:
            raw_xml = response.read()
        try:
            xml = ElementTree.fromstring(raw_xml)
            return self.parse_standings(xml, phase_id)
        except ElementTree.ParseError:
            return None

    def parse_season(self, xml: ElementTree.Element,
                     year: int) -> Optional[Season]:
        divisions = []
        for div in xml.findall('div'):
            parsed_division = self.parse_division(div)
            if parsed_division is None:
                print("Failed to parse division", file=sys.stderr)
                continue
            divisions.append(parsed_division)
        return Season(year, divisions)

    def parse_phase(self, xml: ElementTree.Element) -> Optional[Phase]:
        phase_id = int(xml.findtext('id', ''))
        phase_name = xml.findtext('name', '')

        schedule = self.fetch_schedule(phase_id)
        if not schedule:
            return None

        standings = self.fetch_standings(phase_id)
        if not standings:
            return None

        return Phase(phase_id, phase_name, schedule, standings)

    def parse_division(self, xml: ElementTree.Element) -> Optional[Division]:
        division_id = int(xml.findtext('id', ''))
        division_name = xml.findtext('name', '')
        phases = []
        for phase_xml in xml.findall('phases/phase'):
            phase = self.parse_phase(phase_xml)
            if not phase:
                continue
            phases.append(phase)
        return Division(division_id, division_name, phases)

    def parse_schedule(self, xml: ElementTree.Element,
                       phase_id: int) -> Optional[Schedule]:
        matches = []
        for match_xml in xml.findall('game'):
            match = self.parse_match(match_xml)
            if not match:
                continue
            matches.append(match)
        return Schedule(phase_id, matches)

    def parse_standings(self, xml: ElementTree.Element,
                        phase_id: int) -> Optional[Standings]:
        team_standings = []
        for team_standing_xml in xml.findall('team'):
            team_standing = self.parse_team_standing(team_standing_xml)
            if not team_standing:
                continue
            team_standings.append(team_standing)
        return Standings(phase_id, team_standings)

    def parse_team_standing(self, xml: ElementTree.Element) -> Optional[TeamStanding]:
        position = int(xml.findtext('pos', ''))
        team_id = int(xml.findtext('id', ''))
        team_name = xml.findtext('name', '')
        abbr = xml.findtext('abbr', '')
        games_played = int(xml.findtext('gp', ''))
        games_won = int(xml.findtext('gw', ''))
        games_lost = int(xml.findtext('gl', ''))
        points_scored = int(xml.findtext('sp', ''))
        points_allowed = int(xml.findtext('sm', ''))
        # THIS IS STUPID, Kooperativa NBL returns win % here as float
        points = xml.findtext('pt', '')
        return TeamStanding(team_id, team_name, abbr, position,
                            games_played, games_won, games_lost,
                            points_scored, points_allowed, points)

    def parse_team(self, xml: ElementTree.Element) -> Optional[Team]:
        team_id = int(xml.findtext('id', ''))
        team_name = xml.findtext('name', '')
        abbr = xml.findtext('abbr', '')
        return Team(team_id, team_name, abbr)

    def parse_match_result(self, xml: ElementTree.Element) -> Optional[Match.Result]:
        pts = (int(xml.findtext('pts/a', '')), int(xml.findtext('pts/b', '')))
        score = (int(xml.findtext('score/a', '')),
                 int(xml.findtext('score/b', '')))
        partials = dict()
        for partial in xml.findall('partials/partial'):
            partials[partial.get('ord', '')] = (
                int(partial.findtext('a', '')),
                int(partial.findtext('b', ''))
            )
        url_live = xml.findtext('urllive', '')
        return Match.Result(pts, score, partials, url_live)

    def parse_referee(self, xml: ElementTree.Element) -> Optional[Referee]:
        ref_id: int = int(xml.findtext('id', ''))
        first_name: str = xml.findtext('firstname', '')
        last_name: str = xml.findtext('lastname', '')
        return Referee(ref_id, first_name, last_name)

    def parse_match(self, xml: ElementTree.Element) -> Optional[Match]:
        match_id = int(xml.findtext('id', ''))
        gdate = xml.findtext('gdate', '')
        gtime = xml.findtext('gtime', '')
        start = None
        if gdate and gtime and gdate != '0000-00-00':
            cz = pytz.timezone("Europe/Prague")
            start = cz.localize(datetime.strptime(gdate + ' ' + gtime,
                                                  '%Y-%m-%d %H:%M:%S'))
        if not start:
            return None
        place = xml.findtext('place', '')
        city = xml.findtext('city', '')
        refs = []
        for ref_elem in xml.findall('ref'):
            ref = self.parse_referee(ref_elem)
            if not ref:
                continue
            refs.append(ref)
        supervisor = None
        supervisor_elem = xml.find('sup')
        if supervisor_elem:
            supervisor = self.parse_referee(supervisor_elem)
        home_team_element = xml.find('team[@guest="0"]')
        if not home_team_element:
            return None
        home_team = self.parse_team(home_team_element)
        if not home_team:
            return None

        visiting_team_element = xml.find('team[@guest="1"]')
        if not visiting_team_element:
            return None
        visiting_team = self.parse_team(visiting_team_element)
        if not visiting_team:
            return None

        result = None
        result_elem = xml.find('result')
        if not result_elem:
            return None
        result = self.parse_match_result(result_elem)
        return Match(match_id, home_team, visiting_team,
                     start, Match.Location(place, city),
                     refs, supervisor,
                     result)


class CbfApiFetcher_v2:
    def __init__(self):
        pass

    def parse_match(self, match: dict) -> Optional[Match]:
        if not isinstance(match, dict):
            return None

        match_game_info = match['gameInfo'][0]
        if not isinstance(match_game_info, dict):
            return None

        gdate = match_game_info['gdate']
        gtime = match_game_info['gtime']
        start = None
        if gdate and gtime and gdate != '0000-00-00':
            cz = pytz.timezone("Europe/Prague")
            start = cz.localize(
                datetime.strptime(
                    gdate + ' ' + gtime,
                    '%Y-%m-%d %H:%M:%S'
                )).astimezone(pytz.utc)
        if not start:
            return None

        refs = list[Referee]()
        if match_game_info['u1id'] is not None and \
                match_game_info['u1n1'] is not None and \
                match_game_info['u1n2'] is not None:
            refs.append(
                Referee(
                    match_game_info['u1id'],
                    match_game_info['u1n1'],
                    match_game_info['u1n2']
                )
            )

        if match_game_info['u2id'] is not None and \
                match_game_info['u2n1'] is not None and \
                match_game_info['u2n2'] is not None:
            refs.append(
                Referee(
                    match_game_info['u2id'],
                    match_game_info['u2n1'],
                    match_game_info['u2n2']
                )
            )

        if match_game_info['u3id'] is not None and \
                match_game_info['u3n1'] is not None and \
                match_game_info['u3n2'] is not None:
            refs.append(
                Referee(
                    match_game_info['u3id'],
                    match_game_info['u3n1'],
                    match_game_info['u3n2']
                )
            )

        commisar: Optional[Referee] = None
        if match_game_info['commisarid'] is not None and \
                match_game_info['commisarn1'] is not None and \
                match_game_info['commisarn2'] is not None:
            commisar = Referee(
                match_game_info['commisarid'],
                match_game_info['commisarn1'],
                match_game_info['commisarn2']
            )

        match_result: Optional[Match.Result] = None
        live_url: Optional[str] = match_game_info['url_live']
        if match_game_info['points_home'] is not None and \
                match_game_info['points_guest'] is not None and \
                match_game_info['score_home'] is not None and \
                match_game_info['score_guest'] is not None and \
                match_game_info['score_quarter'] is not None:
            partials = dict(
                map(
                    lambda quarter: (str(quarter[0]), tuple(
                        quarter[1].split(':'))),
                    enumerate(match_game_info['score_quarter'].split(' '))
                )
            )
            match_result = Match.Result(
                (
                    match_game_info['points_home'],
                    match_game_info['points_guest']
                ),
                (
                    match_game_info['score_home'],
                    match_game_info['score_guest']
                ),
                partials,
                "" if live_url is None else live_url
            )

        return Match(
            match_game_info['IDgame'],
            Team(int(match_game_info['taidteam']),
                 match_game_info['taname'],
                 match_game_info['taabbr']),
            Team(int(match_game_info['tbidteam']),
                 match_game_info['tbname'],
                 match_game_info['tbabbr']),
            start,
            Match.Location(
                match_game_info['place'],
                match_game_info['city'],
                (match_game_info['lat'], match_game_info['lon'])
            ),
            refs,
            commisar,  # Supervisor
            match_result
        )

    def fetch_match(self, match_id: int) -> Optional[Match]:
        with urllib.request.urlopen(
                'https://cbf.cz/xml/api/game.php?json=1&game=' + str(match_id)
        ) as reponse:
            raw_json = reponse.read()
        try:
            match = json.loads(raw_json)
        except json.JSONDecodeError:
            return None
        return self.parse_match(match)

    def fetch_team_schedule_for_competition(self, team_id: int, comp_id: int) -> Optional[List[Match]]:
        with urllib.request.urlopen(
            f'https://cbf.cz/xml/api/team.php?json=1&id={
                team_id}&competition={comp_id}'
        ) as response:
            raw_json = response.read()
        try:
            team_info = json.loads(raw_json)
        except json.JSONDecodeError:
            return None
        matches: list[Match] = []
        for match in team_info['match']:
            idTeam = match['IDteam']
            if (idTeam is not None and int(match['IDteam']) != team_id):
                continue
            parsed_match = self.fetch_match(match['gid'])
            if (parsed_match):
                matches.append(parsed_match)
        return matches


def fetch_season_list() -> list[SeasonDescription]:
    with urllib.request.urlopen(
        'http://cbf.cz/xml/api/seasonList.php'
    ) as response:
        raw_xml = response.read()
    season_descriptions: list[SeasonDescription] = []
    try:
        xml = ElementTree.fromstring(raw_xml)
        for season_description in xml.findall('season'):
            season_descriptions.append(
                SeasonDescription.from_xml(season_description))
    except ElementTree.ParseError:
        pass
    return season_descriptions


def find_team(year: int, team_name: str) -> List[Tuple[int, int]]:
    lower_team_name = team_name.lower()
    team_id_and_phases: List[Tuple[int, int]] = []
    fetcher = CbfApiFetcher_v1(cbf_api_endpoint)
    season = fetcher.fetch_season(year)
    if not season:
        return []
    for division in season.divisions:
        for phase in division.phases:
            for team_standing in phase.standings.team_standings:
                if team_standing.name.lower() == lower_team_name:
                    team_id_and_phases.append((phase.id, team_standing.id))
    return team_id_and_phases
