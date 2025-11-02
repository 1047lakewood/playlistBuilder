
class Track:
    def __init__(self, path: str, artist: str = "", title: str = "", duration = None, metadata = None):
        self.path = path
        self.artist = artist
        self.title = title
        self.duration = duration
        self.metadata = metadata
        self.play_time = None
        self.has_intro = False
        self.exists = True
    def __str__(self):
        return f"track at {self.path}"

    def __repr__(self):
        return f"Track(path={self.path}, title={self.title}, duration={self.duration}, metadata={self.metadata}, play_time={self.play_time}, has_intro={self.has_intro})"

    def copy(self):
        return Track(self.path, self.artist, self.title, self.duration, self.metadata)
