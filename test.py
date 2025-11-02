from models.playlist import Playlist
from models.track import Track
from PlaylistService.playlist_service import PlaylistServiceManager
from metadata_edit_dialog import MetadataEditDialog
from calculate_start_times_dialog import CalculateStartTimesDialog

# playlist_service = PlaylistServiceManager()

# playlist_service.load_playlist_from_path("test.m3u8")
# playlist = playlist_service.playlists[0] 
# print(playlist.tracks)

# playlist_service.editor.add_track_to_playlist(playlist, [Track(path="999999999.mp4"), Track(path="8888888.mp4")])
# print(playlist.tracks)
class Test: 
    def __init__(self, controller):
        self.playlist_service = PlaylistServiceManager()
        self.controller = controller
        self.notebook_view = controller.notebook_view
        # self.track = controller.controller_actions.get_selected_tracks()[0]
    def test(self):
        # playlist = self.controller.playlist_service.reload_api_playlist()
        self.playlist_service.create_day_start_times_playlist(self.controller.controller_actions.get_selected_tab().playlist)
    def test2(self):
        dialog = CalculateStartTimesDialog(self.controller.root)
        result = dialog.result
        print(result)
        
        # self.notebook_view.get_tab_state()
