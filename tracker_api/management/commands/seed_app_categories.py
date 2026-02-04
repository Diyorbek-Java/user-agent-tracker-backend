"""
Management command to seed default app categories for productivity tracking.
Usage: python manage.py seed_app_categories
"""
from django.core.management.base import BaseCommand
from tracker_api.models import AppCategory


class Command(BaseCommand):
    help = 'Seed default app categories for productivity tracking'

    # Default categories configuration
    DEFAULT_CATEGORIES = {
        AppCategory.PRODUCTIVE: [
            # IDEs and Development Tools
            ('Code.exe', 'Visual Studio Code'),
            ('devenv.exe', 'Visual Studio'),
            ('pycharm64.exe', 'PyCharm'),
            ('idea64.exe', 'IntelliJ IDEA'),
            ('webstorm64.exe', 'WebStorm'),
            ('sublime_text.exe', 'Sublime Text'),
            ('notepad++.exe', 'Notepad++'),
            ('atom.exe', 'Atom'),
            ('eclipse.exe', 'Eclipse'),
            ('AndroidStudio.exe', 'Android Studio'),

            # Microsoft Office
            ('WINWORD.EXE', 'Microsoft Word'),
            ('EXCEL.EXE', 'Microsoft Excel'),
            ('POWERPNT.EXE', 'Microsoft PowerPoint'),
            ('OUTLOOK.EXE', 'Microsoft Outlook'),
            ('ONENOTE.EXE', 'Microsoft OneNote'),
            ('MSACCESS.EXE', 'Microsoft Access'),

            # Communication & Collaboration (Work)
            ('Slack.exe', 'Slack'),
            ('Teams.exe', 'Microsoft Teams'),
            ('Zoom.exe', 'Zoom'),
            ('webex.exe', 'Cisco Webex'),

            # Design Tools
            ('Figma.exe', 'Figma'),
            ('Photoshop.exe', 'Adobe Photoshop'),
            ('Illustrator.exe', 'Adobe Illustrator'),
            ('XD.exe', 'Adobe XD'),
            ('AfterFX.exe', 'Adobe After Effects'),
            ('PremierePro.exe', 'Adobe Premiere Pro'),
            ('Sketch.exe', 'Sketch'),

            # Development Tools
            ('git.exe', 'Git'),
            ('docker.exe', 'Docker'),
            ('Postman.exe', 'Postman'),
            ('insomnia.exe', 'Insomnia'),
            ('terminal.exe', 'Terminal'),
            ('WindowsTerminal.exe', 'Windows Terminal'),
            ('cmd.exe', 'Command Prompt'),
            ('powershell.exe', 'PowerShell'),

            # Database Tools
            ('mysql.exe', 'MySQL'),
            ('pgAdmin4.exe', 'pgAdmin'),
            ('dbeaver.exe', 'DBeaver'),
            ('DataGrip.exe', 'DataGrip'),

            # Project Management
            ('jira.exe', 'Jira'),
            ('notion.exe', 'Notion'),
            ('asana.exe', 'Asana'),
            ('trello.exe', 'Trello'),
        ],

        AppCategory.NON_PRODUCTIVE: [
            # Streaming & Entertainment
            ('YouTube', 'YouTube'),
            ('Netflix', 'Netflix'),
            ('Twitch', 'Twitch'),
            ('Spotify.exe', 'Spotify'),
            ('vlc.exe', 'VLC Media Player'),

            # Social Media
            ('Facebook', 'Facebook'),
            ('Instagram', 'Instagram'),
            ('TikTok', 'TikTok'),
            ('Twitter', 'Twitter'),
            ('reddit', 'Reddit'),
            ('snapchat', 'Snapchat'),

            # Gaming
            ('Steam.exe', 'Steam'),
            ('EpicGamesLauncher.exe', 'Epic Games Launcher'),
            ('Discord.exe', 'Discord'),
            ('Battle.net.exe', 'Battle.net'),
            ('Origin.exe', 'Origin'),
            ('GTA5.exe', 'GTA V'),
            ('LeagueClient.exe', 'League of Legends'),
            ('VALORANT.exe', 'Valorant'),
            ('csgo.exe', 'CS:GO'),
            ('Minecraft.exe', 'Minecraft'),

            # Shopping
            ('Amazon', 'Amazon'),
            ('eBay', 'eBay'),
        ],

        AppCategory.NEUTRAL: [
            # Browsers (can't determine intent)
            ('chrome.exe', 'Google Chrome'),
            ('firefox.exe', 'Mozilla Firefox'),
            ('msedge.exe', 'Microsoft Edge'),
            ('opera.exe', 'Opera'),
            ('brave.exe', 'Brave Browser'),
            ('safari', 'Safari'),

            # System Tools
            ('explorer.exe', 'File Explorer'),
            ('notepad.exe', 'Notepad'),
            ('Calculator.exe', 'Calculator'),
            ('SnippingTool.exe', 'Snipping Tool'),
            ('mspaint.exe', 'Paint'),

            # File Management
            ('7zFM.exe', '7-Zip'),
            ('WinRAR.exe', 'WinRAR'),

            # Other
            ('SearchHost.exe', 'Windows Search'),
            ('Settings.exe', 'Windows Settings'),
        ]
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing categories',
        )

    def handle(self, *args, **options):
        force_update = options['force']
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for category, apps in self.DEFAULT_CATEGORIES.items():
            for process_name, display_name in apps:
                existing = AppCategory.objects.filter(process_name__iexact=process_name).first()

                if existing:
                    if force_update:
                        existing.display_name = display_name
                        existing.category = category
                        existing.is_global = True
                        existing.save()
                        updated_count += 1
                        self.stdout.write(f'Updated: {display_name} ({process_name}) -> {category}')
                    else:
                        skipped_count += 1
                else:
                    AppCategory.objects.create(
                        process_name=process_name,
                        display_name=display_name,
                        category=category,
                        is_global=True,
                        description=f'Default {category.lower()} application'
                    )
                    created_count += 1
                    self.stdout.write(f'Created: {display_name} ({process_name}) -> {category}')

        self.stdout.write(self.style.SUCCESS(
            f'\nSeed completed: {created_count} created, {updated_count} updated, {skipped_count} skipped'
        ))
