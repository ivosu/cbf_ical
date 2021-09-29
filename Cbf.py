import xml.etree.ElementTree as ElementTree
import urllib.request
from typing import Tuple, Dict, List, Optional
from datetime import datetime
import pytz

cbf_api_endpoint = "https://www.cbf.cz/xml/"


class Referee:
    def __init__(self, ref_id: int, first_name: str, last_name: str):
        self.id = ref_id
        self.first_name = first_name
        self.last_name = last_name

    @classmethod
    def from_xml(cls, xml: ElementTree.Element):
        ref_id: int = int(xml.find('id').text)
        first_name: str = xml.find('firstname').text
        last_name: str = xml.find('lastname').text
        return cls(ref_id, first_name, last_name)


class Team:
    def __init__(self, team_id: int, team_name: str, abbr: str):
        self.id = team_id
        self.name = team_name
        self.abbr = abbr

    @classmethod
    def from_xml(cls, xml: ElementTree.Element):
        team_id = int(xml.find('id').text)
        team_name = xml.find('name').text
        abbr = xml.find('abbr').text
        return cls(team_id, team_name, abbr)


class Match:
    class Result:
        def __init__(self, pts: Tuple[int, int], score: Tuple[int, int], partials: Dict[str, Tuple[int, int]],
                     url_live: str):
            self.pts = pts
            self.score = score
            self.partials = partials
            self.url_live = url_live

        @classmethod
        def from_xml(cls, xml: ElementTree.Element):
            pts_elem = xml.find('pts')
            pts = (int(pts_elem.find('a').text), int(pts_elem.find('b').text))
            score_elem = xml.find('score')
            score = (int(score_elem.find('a').text), int(score_elem.find('b').text))
            partials_elem = xml.find('partials')
            partials = dict()
            for partial in partials_elem.findall('partial'):
                partials[partial.get('ord')] = (int(partial.find('a').text), int(partial.find('b').text))
            url_live = xml.find('urllive').text
            return cls(pts, score, partials, url_live)

    # possible addition - round
    def __init__(self, team_id: int, home_team: Team, visiting_team: Team, start: Optional[datetime], place: str,
                 city: str, refs: List[Referee], supervisor: Optional[Referee], result: Optional[Result]):
        self.id = team_id
        self.home_team = home_team
        self.visiting_team = visiting_team
        self.start = start
        self.place = place
        self.city = city
        self.refs = refs
        self.supervisor = supervisor
        self.result = result

    @classmethod
    def from_xml(cls, xml: ElementTree.Element):
        match_id = int(xml.find('id').text)
        gdate = xml.find('gdate').text
        gtime = xml.find('gtime').text
        start = None
        if gdate and gtime and gdate != '0000-00-00':
            cz = pytz.timezone("Europe/Prague")
            start = cz.localize(datetime.strptime(gdate + ' ' + gtime, '%Y-%m-%d %H:%M:%S'))
        place = xml.find('place').text
        city = xml.find('city').text
        refs = []
        for ref in xml.findall('ref'):
            refs.append(Referee.from_xml(ref))
        supervisor = None
        supervisor_elem = xml.find('sup')
        if supervisor_elem:
            supervisor = Referee.from_xml(supervisor_elem)
        home_team = Team.from_xml(xml.find('team[@guest="0"]'))
        visiting_team = Team.from_xml(xml.find('team[@guest="1"]'))
        result = None
        result_elem = xml.find('result')
        if result_elem:
            result = Match.Result.from_xml(result_elem)
        return cls(match_id, home_team, visiting_team, start, place, city, refs, supervisor, result)


class Schedule:
    def __init__(self, phase_id: int, matches: List[Match]):
        self.phase_id = phase_id
        self.matches = matches

    @classmethod
    def fetch_from_cbf(cls, phase_id: int):
        with urllib.request.urlopen(cbf_api_endpoint + 'sched.php?p=' + str(phase_id)) as response:
            raw_matches_xml = response.read()
        matches = []
        try:
            matches_xml = ElementTree.fromstring(raw_matches_xml)
            for match in matches_xml.findall('game'):
                matches.append(Match.from_xml(match))
        except ElementTree.ParseError:
            pass
        return cls(phase_id, matches)


class TeamStanding:
    def __init__(self, team_id: int, team_name: str, abbr: str, position: int, games_played: int, games_won: int,
                 games_lost: int, points_scored: int, points_allowed: int, points: str):
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

    @classmethod
    def from_xml(cls, xml: ElementTree.Element):
        position = int(xml.find('pos').text)
        team_id = int(xml.find('id').text)
        team_name = xml.find('name').text
        abbr = xml.find('abbr').text
        games_played = int(xml.find('gp').text)
        games_won = int(xml.find('gw').text)
        games_lost = int(xml.find('gl').text)
        points_scored = int(xml.find('sp').text)
        points_allowed = int(xml.find('sm').text)
        points = xml.find('pt').text # THIS IS STUPID, Kooperativa NBL returns win % here as float
        return cls(team_id, team_name, abbr, position, games_played, games_won, games_lost, points_scored,
                   points_allowed, points)


class Standings:
    def __init__(self, phase_id: int, team_standings: List[TeamStanding]):
        self.phase_id = phase_id
        self.team_standings = team_standings

    @classmethod
    def fetch_from_cbf(cls, phase_id: int):
        with urllib.request.urlopen(cbf_api_endpoint + 'table.php?p=' + str(phase_id)) as response:
            raw_standings_xml = response.read()
        team_standings = []
        try:
            standings_xml = ElementTree.fromstring(raw_standings_xml)
            for team_standing in standings_xml.findall('team'):
                team_standings.append(TeamStanding.from_xml(team_standing))
        except ElementTree.ParseError:
            pass
        return cls(phase_id, team_standings)


class Phase:
    # possible additions - type, offset
    def __init__(self, phase_id: int, phase_name: str, schedule: Schedule, standings: Standings):
        self.id = phase_id
        self.name = phase_name
        self.schedule = schedule
        self.standings = standings

    @classmethod
    def from_xml(cls, xml: ElementTree.Element):
        phase_id = int(xml.find('id').text)
        phase_name = xml.find('name').text
        return cls(phase_id, phase_name, Schedule.fetch_from_cbf(phase_id), Standings.fetch_from_cbf(phase_id))


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

    def __init__(self, division_id: int, division_name: str, phases: List[Phase]):
        self.id = division_id
        self.name = division_name
        self.phases = phases

    @classmethod
    def from_xml(cls, xml: ElementTree.Element):
        division_id = int(xml.find('id').text)
        division_name = xml.find('name').text
        phases = []
        for phase in xml.findall('phases/phase'):
            phases.append(Phase.from_xml(phase))
        return cls(division_id, division_name, phases)


class Season:
    def __init__(self, year: int, divisions: List[Division]):
        self.year = year
        self.divisions = divisions

    @classmethod
    def fetch_from_cbf(cls, year: int):
        with urllib.request.urlopen(cbf_api_endpoint + 'divs.php?s=' + str(year)) as response:
            raw_xml = response.read()
        divisions = []
        try:
            xml = ElementTree.fromstring(raw_xml)
            for div in xml.findall('div'):
                divisions.append(Division.from_xml(div))
        except ElementTree.ParseError:
            pass
        return cls(year, divisions)
