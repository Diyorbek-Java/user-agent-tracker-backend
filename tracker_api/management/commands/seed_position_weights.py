"""
Management command to seed research-based productivity weights per job position.

Weights are based on:
  - SPACE framework (Forsgren et al., 2021)
  - GitLab Developer Productivity Report 2023
  - McKinsey "Measuring developer productivity" research
  - Standard HR / management productivity benchmarks

Weight scale:
  1.0  = pure deep work (maximum output value for this role)
  0.8+ = high-value task (core to the role)
  0.6  = supportive work (necessary overhead)
  0.4  = minor / ambiguous value
  0.2  = mostly distraction, rare legitimate use
  0.0  = zero work output

Usage:
  python manage.py seed_position_weights
  python manage.py seed_position_weights --force   # overwrite existing
  python manage.py seed_position_weights --position "Software developer"
"""
from django.core.management.base import BaseCommand
from tracker_api.models import AppCategory, JobPosition, PositionAppWeight


class Command(BaseCommand):
    help = 'Seed research-based productivity weights per job position'

    # ── Weight tables ───────────────────────────────────────────────────────────
    # Key = AppCategory.process_name (case-insensitive match)
    # Value = weight (0.0–1.0)
    #
    # Rationale per role is documented inline.

    SOFTWARE_DEVELOPER = {
        # Core deep-work coding tools — every second counts as maximum output
        'IntelliJ IDEA':            1.0,   # primary IDE; deep work / flow state
        'Visual Studio Code':       1.0,   # primary editor
        'PyCharm':                  1.0,
        'WebStorm':                 1.0,
        'Visual Studio':            1.0,
        'Android Studio':           1.0,
        'Sublime Text':             0.95,
        'Notepad++':                0.85,  # coding-adjacent, lighter tool
        'Eclipse':                  0.95,
        'CLion':                    1.0,
        'Rider':                    1.0,
        'GoLand':                   1.0,

        # Terminal / CLI — core developer tooling, equal to IDE time
        'Windows Terminal':         1.0,
        'Windows Terminal Host':    1.0,
        'PowerShell':               1.0,
        'Command Prompt':           0.9,
        'Git Bash':                 1.0,
        'Git':                      0.95,

        # DevOps / testing tools — directly part of the dev workflow
        'Docker Desktop':           0.9,
        'Postman':                  0.9,
        'Insomnia':                 0.9,

        # Database tools — querying / schema work is legit dev time
        'DBeaver':                  0.85,
        'pgAdmin 4':                0.85,
        'DataGrip':                 0.85,
        'MySQL Workbench':          0.85,

        # Project & knowledge management
        'Jira':                     0.75,  # planning, sprint tracking
        'Notion':                   0.70,
        'Trello':                   0.65,
        'Asana':                    0.65,
        'Linear':                   0.75,
        'ClickUp':                  0.65,

        # Documentation (Word, OneNote) — useful but not core dev output
        'Microsoft Word':           0.65,
        'Microsoft OneNote':        0.70,
        'Microsoft Excel':          0.55,  # data analysis, occasional use
        'Microsoft PowerPoint':     0.45,  # presentations, rare for devs

        # AI productivity tools — accelerate output
        'Microsoft Copilot':        0.85,
        'GitHub Copilot':           1.0,

        # Communication — necessary overhead, disrupts deep work
        # Research shows 23 min to regain focus after interruption (Gloria Mark, 2004)
        'Slack':                    0.60,
        'Microsoft Teams':          0.55,
        'Zoom':                     0.55,
        'Zoom Meetings':            0.55,
        'Microsoft Outlook':        0.50,  # email = primarily overhead for devs
        'Cisco Webex':              0.50,
        'Cisco AnyConnect User Interface':  0.20,  # VPN connect, near-instant

        # Design tools — occasionally used by full-stack devs
        'Figma':                    0.45,
        'Adobe XD':                 0.35,
        'Adobe Photoshop':          0.30,
        'Adobe Illustrator':        0.25,

        # Browsers — mix of documentation research and distraction
        # Devs DO use browser for docs (MDN, SO) but also social / YouTube
        # Conservative 0.35 reflects the realistic mix
        'Google Chrome':            0.35,
        'Mozilla Firefox':          0.35,
        'Microsoft Edge':           0.30,
        'Brave Browser':            0.35,
        'Opera':                    0.30,

        # File & system utilities — occasional file management
        'Windows Explorer':         0.20,
        'File Explorer':            0.20,
        'WinRAR':                   0.15,
        '7-Zip':                    0.15,
        'Notepad':                  0.30,  # quick scratch notes
        'SnippingTool':             0.25,  # screenshot for docs/bug reports
        'Calculator':               0.15,

        # Non-productive (these are in the DB so we must set explicit weights)
        'LockApp.exe':              0.0,   # screen locked = not at desk
        'Telegram Desktop':         0.05,  # personal chat, almost no work value
        'Discord':                  0.15,  # some dev community use
        'Settings':                 0.05,
        'Steam':                    0.0,
        'Steam Client WebHelper':   0.0,
        'Cs2':                      0.0,
        'Counter-Strike 2':         0.0,
        'Spotify':                  0.0,
        'ShellHost':                0.0,
        'Windows Shell Experience Host':    0.0,
        'Microsoft® Windows® Operating System': 0.0,
        'Windows host process (Rundll32)':  0.0,
        'Windows Start Experience Host':    0.0,
        'WinStore.App':             0.0,
        'Application Frame Host':   0.10,  # UWP app container
        'File Picker UI Host':      0.10,  # file open dialog
    }

    MANAGER = {
        # Communication is the manager's primary output instrument
        'Slack':                    0.95,
        'Microsoft Teams':          0.95,
        'Microsoft Outlook':        0.90,
        'Zoom':                     0.90,
        'Zoom Meetings':            0.90,
        'Cisco Webex':              0.85,

        # Documents / presentations — core deliverables
        'Microsoft Word':           0.95,
        'Microsoft Excel':          0.95,
        'Microsoft PowerPoint':     0.90,
        'Microsoft OneNote':        0.85,
        'Microsoft Access':         0.70,

        # Project management — managers live here
        'Jira':                     0.90,
        'Asana':                    0.90,
        'Notion':                   0.85,
        'Trello':                   0.85,
        'Linear':                   0.85,
        'ClickUp':                  0.85,

        # AI tools
        'Microsoft Copilot':        0.80,

        # VPN
        'Cisco AnyConnect User Interface':  0.15,

        # Browsers — more legitimate research use for managers
        'Google Chrome':            0.50,
        'Mozilla Firefox':          0.50,
        'Microsoft Edge':           0.50,
        'Brave Browser':            0.45,
        'Opera':                    0.45,

        # Dev tools — managers occasionally do code reviews
        'IntelliJ IDEA':            0.35,
        'Visual Studio Code':       0.35,
        'PyCharm':                  0.30,
        'Windows Terminal':         0.40,
        'Windows Terminal Host':    0.40,

        # Utilities
        'Windows Explorer':         0.25,
        'File Explorer':            0.25,
        'Notepad':                  0.35,
        'SnippingTool':             0.30,
        'Calculator':               0.20,
        'WinRAR':                   0.15,
        '7-Zip':                    0.15,

        # Non-productive
        'LockApp.exe':              0.0,
        'Telegram Desktop':         0.10,
        'Discord':                  0.05,
        'Settings':                 0.05,
        'Steam':                    0.0,
        'Steam Client WebHelper':   0.0,
        'Cs2':                      0.0,
        'Spotify':                  0.0,
        'ShellHost':                0.0,
        'Windows Shell Experience Host':    0.0,
        'Microsoft® Windows® Operating System': 0.0,
        'Windows host process (Rundll32)':  0.0,
        'WinStore.App':             0.0,
        'Application Frame Host':   0.10,
        'File Picker UI Host':      0.10,
    }

    # Map of position title keywords → weight table
    # Matched case-insensitively against JobPosition.title
    POSITIONS = {
        'software':     SOFTWARE_DEVELOPER,
        'developer':    SOFTWARE_DEVELOPER,
        'engineer':     SOFTWARE_DEVELOPER,
        'programmer':   SOFTWARE_DEVELOPER,
        'manager':      MANAGER,
        'lead':         MANAGER,
        'director':     MANAGER,
        'head':         MANAGER,
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing weights',
        )
        parser.add_argument(
            '--position',
            type=str,
            default=None,
            help='Seed only this position title (partial match)',
        )

    def handle(self, *args, **options):
        force = options['force']
        only_pos = options.get('position', '').lower() if options.get('position') else None

        positions = JobPosition.objects.filter(is_active=True)
        if only_pos:
            positions = positions.filter(title__icontains=only_pos)

        if not positions.exists():
            self.stdout.write(self.style.WARNING('No active job positions found. Create positions first.'))
            return

        total_created = total_updated = total_skipped = 0

        for position in positions:
            weight_table = self._get_weight_table(position.title)
            if not weight_table:
                self.stdout.write(f'  Skipping "{position.title}" — no weight table matched')
                continue

            self.stdout.write(f'\n[{position.title}]')
            created = updated = skipped = 0

            for process_name, weight in weight_table.items():
                app_cat = AppCategory.objects.filter(
                    process_name__iexact=process_name
                ).first()
                if not app_cat:
                    # Auto-create a NEUTRAL placeholder so the weight can be stored
                    app_cat = AppCategory.objects.create(
                        process_name=process_name,
                        display_name=process_name,
                        category=AppCategory.NEUTRAL,
                        is_global=True,
                        description='Auto-created by seed_position_weights'
                    )

                pw, was_created = PositionAppWeight.objects.get_or_create(
                    position=position,
                    app_category=app_cat,
                    defaults={'weight': weight}
                )

                if was_created:
                    created += 1
                elif force and abs(pw.weight - weight) > 0.001:
                    pw.weight = weight
                    pw.save()
                    updated += 1
                    self.stdout.write(f'    Updated: {process_name} → {weight}')
                else:
                    skipped += 1

            self.stdout.write(
                f'  {created} created, {updated} updated, {skipped} skipped'
            )
            total_created += created
            total_updated += updated
            total_skipped += skipped

        self.stdout.write(self.style.SUCCESS(
            f'\nTotal: {total_created} created, {total_updated} updated, {total_skipped} skipped'
        ))

    def _get_weight_table(self, title: str) -> dict:
        title_lower = title.lower()
        for keyword, table in self.POSITIONS.items():
            if keyword in title_lower:
                return table
        return {}
