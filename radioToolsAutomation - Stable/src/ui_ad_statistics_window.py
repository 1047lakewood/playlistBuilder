import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import logging
import os
import json

class AdStatisticsWindow:
    """Window to display ad play statistics with tabs for each station."""

    def __init__(self, parent, config_manager):
        """
        Initialize the Ad Statistics window.

        Args:
            parent: Parent tkinter window
            config_manager: ConfigManager instance
        """
        self.parent = parent
        self.config_manager = config_manager
        
        # Dictionary to store station-specific data
        self.stations = {
            'station_1047': {
                'name': '104.7 FM',
                'ad_logger': None,
                'report_generator': None,
                'widgets': {},
                'date_filter_active': False,
                'sort_column_name': None,
                'sort_reverse': False
            },
            'station_887': {
                'name': '88.7 FM',
                'ad_logger': None,
                'report_generator': None,
                'widgets': {},
                'date_filter_active': False,
                'sort_column_name': None,
                'sort_reverse': False
            }
        }
        
        # Initialize ad loggers for both stations
        try:
            from ad_play_logger import AdPlayLogger
            from ad_report_generator import AdReportGenerator
            
            for station_id in self.stations.keys():
                self.stations[station_id]['ad_logger'] = AdPlayLogger(config_manager, station_id)
                self.stations[station_id]['report_generator'] = AdReportGenerator(
                    self.stations[station_id]['ad_logger'], station_id
                )
        except ImportError as e:
            logging.error(f"Failed to import ad modules: {e}")

        self.window = tk.Toplevel(parent)
        self.window.title("Ad Play Statistics")
        self.window.geometry("1050x750")
        self.window.minsize(950, 650)

        # Make window modal
        self.window.transient(parent)
        self.window.grab_set()

        # Center the window
        self._center_window()

        self.create_widgets()
        
        # Refresh stats for both stations
        for station_id in self.stations.keys():
            self.refresh_stats(station_id)

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def _center_window(self):
        """Center the window on the screen."""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'+{x}+{y}')

    def create_widgets(self):
        """Create and arrange all widgets."""
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create a tab for each station
        for station_id, station_data in self.stations.items():
            tab_frame = ttk.Frame(notebook, padding="10")
            notebook.add(tab_frame, text=station_data['name'])
            self.create_station_tab(tab_frame, station_id)
        
        # Close button at bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        ttk.Button(button_frame, text="Close", command=self.on_close).pack(side=tk.RIGHT, padx=5)

    def create_station_tab(self, parent_frame, station_id):
        """Create the statistics interface for a specific station."""
        station_data = self.stations[station_id]
        widgets = station_data['widgets']
        
        # Control buttons and date filters
        controls_frame = ttk.Frame(parent_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))

        # Date filter section
        filter_frame = ttk.LabelFrame(controls_frame, text="Date Filter", padding="10")
        filter_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        ttk.Label(filter_frame, text="From:").grid(row=0, column=0, sticky=tk.W, padx=5)
        widgets['start_date_var'] = tk.StringVar()
        widgets['start_date_entry'] = ttk.Entry(filter_frame, textvariable=widgets['start_date_var'], width=12)
        widgets['start_date_entry'].grid(row=0, column=1, padx=5)
        widgets['start_date_entry'].insert(0, "YYYY-MM-DD")
        widgets['start_date_entry'].configure(foreground="gray")

        ttk.Label(filter_frame, text="To:").grid(row=0, column=2, sticky=tk.W, padx=5)
        widgets['end_date_var'] = tk.StringVar()
        widgets['end_date_entry'] = ttk.Entry(filter_frame, textvariable=widgets['end_date_var'], width=12)
        widgets['end_date_entry'].grid(row=0, column=3, padx=5)
        widgets['end_date_entry'].insert(0, "YYYY-MM-DD")
        widgets['end_date_entry'].configure(foreground="gray")

        ttk.Button(filter_frame, text="Apply", command=lambda: self.apply_date_filter(station_id), width=8).grid(row=0, column=4, padx=5)
        ttk.Button(filter_frame, text="Clear", command=lambda: self.clear_date_filter(station_id), width=8).grid(row=0, column=5, padx=5)

        # Action buttons
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(side=tk.RIGHT)

        button_row1 = ttk.Frame(button_frame)
        button_row1.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(button_row1, text="Refresh Stats", command=lambda: self.refresh_stats(station_id), width=14).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_row1, text="Reset Counts", command=lambda: self.reset_counts(station_id), width=14).pack(side=tk.LEFT, padx=2)

        button_row2 = ttk.Frame(button_frame)
        button_row2.pack(fill=tk.X)
        ttk.Button(button_row2, text="Export Stats", command=lambda: self.export_stats(station_id), width=14).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_row2, text="Generate Report", command=lambda: self.generate_advertiser_report(station_id), width=14).pack(side=tk.LEFT, padx=2)

        # Statistics summary
        summary_frame = ttk.LabelFrame(parent_frame, text="Summary", padding="10")
        summary_frame.pack(fill=tk.X, pady=(0, 10))

        widgets['summary_labels'] = {}
        summary_grid = [
            ("Total Ads:", "total_ads"),
            ("Enabled Ads:", "enabled_ads"),
            ("Total Plays:", "total_plays"),
            ("Ads with Plays:", "ads_with_plays"),
        ]

        for i, (label_text, key) in enumerate(summary_grid):
            label = ttk.Label(summary_frame, text=label_text)
            label.grid(row=i//2, column=(i%2)*2, sticky=tk.W, padx=5, pady=2)

            value_label = ttk.Label(summary_frame, text="0", font=("Segoe UI", 10, "bold"))
            value_label.grid(row=i//2, column=(i%2)*2 + 1, sticky=tk.W, padx=5, pady=2)
            widgets['summary_labels'][key] = value_label

        # Ad details table
        table_frame = ttk.LabelFrame(parent_frame, text="Ad Details", padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Create treeview for ad details
        columns = ("Name", "Status", "Play Count", "Last Played", "File")
        widgets['ad_tree'] = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)

        # Define column headings
        for col in columns:
            widgets['ad_tree'].heading(col, text=col, command=lambda c=col, s=station_id: self.sort_column(s, c))
            widgets['ad_tree'].column(col, width=120, minwidth=80)

        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=widgets['ad_tree'].yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=widgets['ad_tree'].xview)
        widgets['ad_tree'].configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Pack scrollbars and treeview
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        widgets['ad_tree'].pack(fill=tk.BOTH, expand=True)

        # Status bar
        widgets['status_var'] = tk.StringVar(value="Ready")
        status_bar = ttk.Label(parent_frame, textvariable=widgets['status_var'], relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(10, 0))

    def refresh_stats(self, station_id):
        """Refresh and display current ad statistics for a specific station."""
        station_data = self.stations[station_id]
        ad_logger = station_data['ad_logger']
        widgets = station_data['widgets']
        
        if not ad_logger:
            messagebox.showerror("Error", "Ad logging system not available", parent=self.window)
            return

        try:
            widgets['status_var'].set("Refreshing statistics...")
            self.window.update()

            # Use filtered or unfiltered stats based on current filter state
            if station_data['date_filter_active']:
                start_date = widgets['start_date_var'].get().strip()
                end_date = widgets['end_date_var'].get().strip()

                if not start_date or not end_date or start_date == "YYYY-MM-DD" or end_date == "YYYY-MM-DD":
                    messagebox.showerror("Error", "Please enter both start and end dates for filtering.", parent=self.window)
                    return

                stats = ad_logger.get_ad_statistics_filtered(start_date, end_date)
            else:
                stats = ad_logger.get_ad_statistics()

            if "error" in stats:
                messagebox.showerror("Error", f"Failed to get statistics: {stats['error']}", parent=self.window)
                return

            # Update summary labels
            widgets['summary_labels']["total_ads"].config(text=str(stats.get("total_ads", 0)))
            widgets['summary_labels']["enabled_ads"].config(text=str(stats.get("enabled_ads", 0)))
            widgets['summary_labels']["total_plays"].config(text=str(stats.get("total_plays", 0)))
            widgets['summary_labels']["ads_with_plays"].config(text=str(stats.get("ads_with_plays", 0)))

            # Clear existing items
            for item in widgets['ad_tree'].get_children():
                widgets['ad_tree'].delete(item)

            # Add ad details
            for ad in stats.get("ad_details", []):
                name = ad.get("name", "Unknown")
                status = "Enabled" if ad.get("enabled", False) else "Disabled"
                play_count = ad.get("play_count", 0)
                last_played = ad.get("last_played", "Never")
                if last_played and last_played != "Never":
                    try:
                        last_played = datetime.fromisoformat(last_played).strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                mp3_file = os.path.basename(ad.get("mp3_file", ""))

                widgets['ad_tree'].insert("", tk.END, values=(name, status, play_count, last_played, mp3_file))

            widgets['status_var'].set(f"Loaded {len(stats.get('ad_details', []))} ads")

        except Exception as e:
            logging.error(f"Error refreshing statistics for {station_id}: {e}")
            messagebox.showerror("Error", f"Failed to refresh statistics: {e}", parent=self.window)
            widgets['status_var'].set("Error loading statistics")

    def apply_date_filter(self, station_id):
        """Apply date filter for a specific station."""
        station_data = self.stations[station_id]
        station_data['date_filter_active'] = True
        self.refresh_stats(station_id)

    def clear_date_filter(self, station_id):
        """Clear date filter for a specific station."""
        station_data = self.stations[station_id]
        widgets = station_data['widgets']
        
        station_data['date_filter_active'] = False
        widgets['start_date_var'].set("")
        widgets['end_date_var'].set("")
        widgets['start_date_entry'].insert(0, "YYYY-MM-DD")
        widgets['start_date_entry'].configure(foreground="gray")
        widgets['end_date_entry'].insert(0, "YYYY-MM-DD")
        widgets['end_date_entry'].configure(foreground="gray")
        self.refresh_stats(station_id)

    def reset_counts(self, station_id):
        """Reset all play counts for a specific station."""
        station_data = self.stations[station_id]
        ad_logger = station_data['ad_logger']
        
        if not ad_logger:
            return

        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset all play counts? This cannot be undone.", parent=self.window):
            if ad_logger.reset_all_play_counts():
                self.refresh_stats(station_id)
            else:
                messagebox.showerror("Error", "Failed to reset play counts.", parent=self.window)

    def export_stats(self, station_id):
        """Export statistics to JSON file for a specific station."""
        station_data = self.stations[station_id]
        ad_logger = station_data['ad_logger']
        
        if not ad_logger:
            return

        filename = filedialog.asksaveasfilename(
            title="Export Statistics",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            parent=self.window
        )
        if filename:
            try:
                stats = ad_logger.get_ad_statistics()
                with open(filename, 'w') as f:
                    json.dump(stats, f, indent=2)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export statistics: {e}", parent=self.window)

    def generate_advertiser_report(self, station_id):
        """Generate advertiser report for a specific station."""
        station_data = self.stations[station_id]
        report_generator = station_data['report_generator']
        
        if not report_generator:
            messagebox.showerror("Error", "Report generator not available", parent=self.window)
            return

        # Use date filter if active
        start_date = None
        end_date = None
        if station_data['date_filter_active']:
            widgets = station_data['widgets']
            start_date = widgets['start_date_var'].get().strip()
            end_date = widgets['end_date_var'].get().strip()
            if start_date == "YYYY-MM-DD":
                start_date = None
            if end_date == "YYYY-MM-DD":
                end_date = None

        try:
            csv_path, pdf_path = report_generator.generate_report(start_date, end_date)
        except Exception as e:
            logging.error(f"Error generating report for {station_id}: {e}")
            messagebox.showerror("Error", f"Failed to generate report: {e}", parent=self.window)

    def sort_column(self, station_id, col):
        """Sort table by column for a specific station."""
        station_data = self.stations[station_id]
        widgets = station_data['widgets']
        tree = widgets['ad_tree']
        
        # Toggle sort direction
        if station_data['sort_column_name'] == col:
            station_data['sort_reverse'] = not station_data['sort_reverse']
        else:
            station_data['sort_reverse'] = False
            station_data['sort_column_name'] = col

        # Get all items
        items = [(tree.set(item, col), item) for item in tree.get_children('')]

        # Sort items
        col_index = {"Name": 0, "Status": 1, "Play Count": 2, "Last Played": 3, "File": 4}
        if col == "Play Count":
            items.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=station_data['sort_reverse'])
        else:
            items.sort(key=lambda x: x[0], reverse=station_data['sort_reverse'])

        # Rearrange items
        for index, (val, item) in enumerate(items):
            tree.move(item, '', index)

    def on_close(self):
        """Handle window close event."""
        self.window.destroy()

