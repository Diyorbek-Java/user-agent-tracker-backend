"""
Management command to seed default app categories for productivity tracking.
Uses the display names that Windows / the C++ agent actually reports as process_name.

Usage:
  python manage.py seed_app_categories          # create new, skip existing
  python manage.py seed_app_categories --force  # overwrite existing entries
"""
from django.core.management.base import BaseCommand
from tracker_api.models import AppCategory


class Command(BaseCommand):
    help = 'Seed default app categories (uses Windows display names, not .exe names)'

    DEFAULT_CATEGORIES = {
        # ── PRODUCTIVE ──────────────────────────────────────────────────────────
        # Every second in these apps is billable development / office work.
        AppCategory.PRODUCTIVE: [
            # IDEs & editors (deep-work, highest output value)
            ('IntelliJ IDEA',            'IntelliJ IDEA'),
            ('Visual Studio Code',       'Visual Studio Code'),
            ('PyCharm',                  'PyCharm'),
            ('WebStorm',                 'WebStorm'),
            ('Visual Studio',            'Visual Studio'),
            ('Android Studio',           'Android Studio'),
            ('Sublime Text',             'Sublime Text'),
            ('Notepad++',                'Notepad++'),
            ('Eclipse',                  'Eclipse'),
            ('CLion',                    'CLion'),
            ('Rider',                    'Rider'),
            ('GoLand',                   'GoLand'),

            # Terminals / CLI (core developer tooling)
            ('Windows Terminal',         'Windows Terminal'),
            ('Windows Terminal Host',    'Windows Terminal Host'),
            ('PowerShell',               'PowerShell'),
            ('Command Prompt',           'Command Prompt'),
            ('Git Bash',                 'Git Bash'),

            # DevOps / build tools
            ('Docker Desktop',           'Docker Desktop'),
            ('Postman',                  'Postman'),
            ('Insomnia',                 'Insomnia'),
            ('Git',                      'Git'),

            # Database tools
            ('DBeaver',                  'DBeaver'),
            ('pgAdmin 4',                'pgAdmin'),
            ('DataGrip',                 'DataGrip'),
            ('MySQL Workbench',          'MySQL Workbench'),

            # Microsoft Office suite
            ('Microsoft Word',           'Microsoft Word'),
            ('Microsoft Excel',          'Microsoft Excel'),
            ('Microsoft PowerPoint',     'Microsoft PowerPoint'),
            ('Microsoft Outlook',        'Microsoft Outlook'),
            ('Microsoft OneNote',        'Microsoft OneNote'),
            ('Microsoft Access',         'Microsoft Access'),
            ('Microsoft Teams',          'Microsoft Teams'),

            # Communication & collaboration
            ('Slack',                    'Slack'),
            ('Zoom',                     'Zoom'),
            ('Zoom Meetings',            'Zoom Meetings'),
            ('Cisco Webex',              'Cisco Webex'),
            ('Webex',                    'Webex'),

            # Design tools
            ('Figma',                    'Figma'),
            ('Adobe Photoshop',          'Adobe Photoshop'),
            ('Adobe Illustrator',        'Adobe Illustrator'),
            ('Adobe XD',                 'Adobe XD'),
            ('Adobe After Effects',      'Adobe After Effects'),
            ('Adobe Premiere Pro',       'Adobe Premiere Pro'),
            ('Sketch',                   'Sketch'),

            # Project management (browser-based apps show as display names)
            ('Jira',                     'Jira'),
            ('Notion',                   'Notion'),
            ('Asana',                    'Asana'),
            ('Trello',                   'Trello'),
            ('Linear',                   'Linear'),
            ('ClickUp',                  'ClickUp'),

            # AI / copilot tools — genuinely boost output
            ('Microsoft Copilot',        'Microsoft Copilot'),
            ('GitHub Copilot',           'GitHub Copilot'),

            # VPN (network access for remote work)
            ('Cisco AnyConnect User Interface',         'Cisco AnyConnect'),
            ('Cisco AnyConnect Secure Mobility Client Downloader',
                                         'Cisco AnyConnect Installer'),
        ],

        # ── NON-PRODUCTIVE ──────────────────────────────────────────────────────
        # These consume time with zero work output.
        AppCategory.NON_PRODUCTIVE: [
            # Lock screen / idle — user is AWAY from the computer
            ('LockApp.exe',              'Windows Lock Screen'),

            # Personal messaging
            ('Telegram Desktop',         'Telegram Desktop'),
            ('WhatsApp',                 'WhatsApp'),
            ('Snapchat',                 'Snapchat'),
            ('Signal',                   'Signal'),
            ('Viber',                    'Viber'),

            # Streaming & entertainment
            ('YouTube',                  'YouTube'),
            ('Netflix',                  'Netflix'),
            ('Twitch',                   'Twitch'),
            ('Spotify',                  'Spotify'),
            ('VLC media player',         'VLC Media Player'),
            ('Windows Media Player',     'Windows Media Player'),

            # Social media
            ('Facebook',                 'Facebook'),
            ('Instagram',                'Instagram'),
            ('TikTok',                   'TikTok'),
            ('Twitter',                  'Twitter'),
            ('X',                        'X (Twitter)'),
            ('Reddit',                   'Reddit'),

            # Gaming
            ('Steam',                    'Steam'),
            ('Steam Client WebHelper',   'Steam Client'),
            ('Epic Games Launcher',      'Epic Games Launcher'),
            ('Discord',                  'Discord'),
            ('Battle.net',               'Battle.net'),
            ('Origin',                   'Origin'),
            ('GTA V',                    'GTA V'),
            ('League of Legends',        'League of Legends'),
            ('Valorant',                 'Valorant'),
            ('Counter-Strike 2',         'Counter-Strike 2'),
            ('Cs2',                      'CS2'),
            ('Minecraft',                'Minecraft'),
            ('Fortnite',                 'Fortnite'),

            # Shopping
            ('Amazon',                   'Amazon'),
            ('eBay',                     'eBay'),

            # Pure system overhead / idle UI that is never "work"
            ('Settings',                 'Windows Settings'),
            ('Microsoft Store',          'Microsoft Store'),
            ('WinStore.App',             'Microsoft Store'),
            ('Windows Start Experience Host', 'Windows Start Menu'),
            ('ShellHost',                'Windows Shell'),
            ('Windows Shell Experience Host', 'Windows Shell Experience'),
            ('Microsoft® Windows® Operating System', 'Windows OS Host'),
            ('Windows host process (Rundll32)', 'Windows Host Process'),
        ],

        # ── NEUTRAL ─────────────────────────────────────────────────────────────
        # Intent depends on the user; scored at default_weight (now 0.3).
        AppCategory.NEUTRAL: [
            # Browsers — can be research or pure distraction
            ('Google Chrome',            'Google Chrome'),
            ('Mozilla Firefox',          'Mozilla Firefox'),
            ('Microsoft Edge',           'Microsoft Edge'),
            ('Opera',                    'Opera'),
            ('Brave Browser',            'Brave Browser'),
            ('Safari',                   'Safari'),
            ('Arc',                      'Arc Browser'),

            # File & system utilities
            ('Windows Explorer',         'Windows Explorer'),
            ('File Explorer',            'File Explorer'),
            ('WinRAR',                   'WinRAR'),
            ('7-Zip',                    '7-Zip'),

            # Light utilities
            ('Notepad',                  'Notepad'),
            ('SnippingTool',             'Snipping Tool'),
            ('Calculator',               'Calculator'),
            ('Paint',                    'Paint'),
            ('Application Frame Host',   'Application Frame Host'),
            ('File Picker UI Host',      'File Picker UI Host'),
        ],
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing categories',
        )

    def handle(self, *args, **options):
        force_update = options['force']
        created = updated = skipped = 0

        for category, apps in self.DEFAULT_CATEGORIES.items():
            for process_name, display_name in apps:
                existing = AppCategory.objects.filter(
                    process_name__iexact=process_name
                ).first()

                if existing:
                    if force_update:
                        existing.display_name = display_name
                        existing.category = category
                        existing.is_global = True
                        existing.save()
                        updated += 1
                        self.stdout.write(f'  Updated: {display_name} → {category}')
                    else:
                        skipped += 1
                else:
                    AppCategory.objects.create(
                        process_name=process_name,
                        display_name=display_name,
                        category=category,
                        is_global=True,
                        description=f'Default {category.lower()} application'
                    )
                    created += 1
                    self.stdout.write(f'  Created: {display_name} → {category}')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone: {created} created, {updated} updated, {skipped} skipped'
        ))
