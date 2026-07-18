"""
Google Slides Deck Generator for Cars Commerce reporting.

Creates branded presentations with data from Tableau, GA, Salesforce.
Outputs a shareable Google Slides link.

Usage:
    from create_deck import SlideDeck
    deck = SlideDeck("Q1 2026 Performance Review")
    deck.add_title_slide("Nalley Lexus Galleria", "Quarterly Business Review — Q1 2026")
    deck.add_metrics_slide("Key Metrics", {"VDP Views": "12,450", "Leads": "342", "SRP→VDP": "3.7%"})
    deck.add_table_slide("Price Badge Summary", headers, rows)
    deck.add_insight_slide("Key Insights", ["VDP views up 15% MoM", "Price badges improved"])
    url = deck.publish()
    print(url)

Auth: Run slides_auth.py first to generate ~/.claude/tokens/slides_credentials.json
"""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime

TOKEN_PATH = os.path.expanduser("~/.claude/tokens/slides_credentials.json")
CLIENT_SECRETS = os.path.expanduser("~/gcp-oauth.keys.json")

# Cars Commerce brand colors
BRAND = {
    "purple_dark": {"red": 0.165, "green": 0.039, "blue": 0.235},   # #2A0A3C
    "purple_accent": {"red": 0.655, "green": 0.302, "blue": 0.808},  # #A74DCE
    "white": {"red": 1.0, "green": 1.0, "blue": 1.0},
    "dark_text": {"red": 0.13, "green": 0.13, "blue": 0.13},
    "light_gray": {"red": 0.95, "green": 0.95, "blue": 0.95},
    "green": {"red": 0.0, "green": 0.6, "blue": 0.3},
    "red": {"red": 0.85, "green": 0.15, "blue": 0.15},
    "blue": {"red": 0.07, "green": 0.34, "blue": 0.80},
}


def _get_credentials():
    """Load and refresh OAuth credentials."""
    if not os.path.exists(TOKEN_PATH):
        raise FileNotFoundError(
            f"No credentials at {TOKEN_PATH}. Run slides_auth.py first."
        )
    with open(TOKEN_PATH) as f:
        tokens = json.load(f)

    # Refresh the access token
    data = urllib.parse.urlencode({
        "client_id": tokens["client_id"],
        "client_secret": tokens["client_secret"],
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        refreshed = json.loads(resp.read())

    tokens["access_token"] = refreshed["access_token"]
    with open(TOKEN_PATH, "w") as f:
        json.dump(tokens, f, indent=2)

    return tokens["access_token"]


def _api(method, url, body=None, token=None):
    """Make an authenticated Google API request."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


class SlideDeck:
    """Build a Google Slides presentation programmatically."""

    BASE = "https://slides.googleapis.com/v1/presentations"

    def __init__(self, title="Untitled Presentation", folder_id=None):
        self.token = _get_credentials()
        self.title = title
        self.folder_id = folder_id
        self._requests = []
        self._slide_count = 0
        self._presentation_id = None
        self._create_presentation()

    def _create_presentation(self):
        """Create a blank presentation via the API."""
        result = _api("POST", self.BASE, {"title": self.title}, self.token)
        self._presentation_id = result["presentationId"]
        # Delete the default blank slide
        default_slide = result["slides"][0]["objectId"]
        self._requests.append({"deleteObject": {"objectId": default_slide}})

    def _new_slide_id(self):
        self._slide_count += 1
        return f"slide_{self._slide_count:03d}"

    def _pt(self, points):
        """Convert points to EMU (English Metric Units)."""
        return {"magnitude": points * 12700, "unit": "EMU"}

    def _text_style(self, font_size=14, bold=False, color=None, font="Proxima Nova"):
        style = {
            "fontSize": self._pt(font_size),
            "fontFamily": font,
        }
        if bold:
            style["bold"] = True
        if color:
            style["foregroundColor"] = {"opaqueColor": {"rgbColor": color}}
        return style

    def add_title_slide(self, title, subtitle=""):
        """Add a branded title slide with dark purple background."""
        slide_id = self._new_slide_id()
        title_id = f"{slide_id}_title"
        subtitle_id = f"{slide_id}_subtitle"

        self._requests.extend([
            {"createSlide": {
                "objectId": slide_id,
                "insertionIndex": self._slide_count - 1,
                "slideLayoutReference": {"predefinedLayout": "BLANK"},
            }},
            # Dark purple background
            {"updatePageProperties": {
                "objectId": slide_id,
                "pageProperties": {
                    "pageBackgroundFill": {
                        "solidFill": {"color": {"rgbColor": BRAND["purple_dark"]}}
                    }
                },
                "fields": "pageBackgroundFill",
            }},
            # Title text box
            {"createShape": {
                "objectId": title_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {"width": self._pt(600), "height": self._pt(80)},
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": 457200, "translateY": 2000000,
                        "unit": "EMU",
                    },
                },
            }},
            {"insertText": {"objectId": title_id, "text": title, "insertionIndex": 0}},
            {"updateTextStyle": {
                "objectId": title_id,
                "style": self._text_style(36, bold=True, color=BRAND["white"]),
                "fields": "fontSize,fontFamily,bold,foregroundColor",
            }},
            # Subtitle
            {"createShape": {
                "objectId": subtitle_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {"width": self._pt(600), "height": self._pt(40)},
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": 457200, "translateY": 3200000,
                        "unit": "EMU",
                    },
                },
            }},
            {"insertText": {"objectId": subtitle_id, "text": subtitle, "insertionIndex": 0}},
            {"updateTextStyle": {
                "objectId": subtitle_id,
                "style": self._text_style(18, color=BRAND["purple_accent"]),
                "fields": "fontSize,fontFamily,foregroundColor",
            }},
        ])
        return slide_id

    def add_metrics_slide(self, title, metrics, subtitle=""):
        """Add a slide with large KPI metric cards.
        metrics: dict of {label: value} — up to 4 recommended.
        """
        slide_id = self._new_slide_id()
        title_id = f"{slide_id}_title"

        self._requests.extend([
            {"createSlide": {
                "objectId": slide_id,
                "insertionIndex": self._slide_count - 1,
                "slideLayoutReference": {"predefinedLayout": "BLANK"},
            }},
            # Title
            {"createShape": {
                "objectId": title_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {"width": self._pt(650), "height": self._pt(50)},
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": 457200, "translateY": 274638,
                        "unit": "EMU",
                    },
                },
            }},
            {"insertText": {"objectId": title_id, "text": title, "insertionIndex": 0}},
            {"updateTextStyle": {
                "objectId": title_id,
                "style": self._text_style(28, bold=True, color=BRAND["purple_dark"]),
                "fields": "fontSize,fontFamily,bold,foregroundColor",
            }},
        ])

        # Metric cards — evenly spaced
        items = list(metrics.items())
        card_width = 170
        gap = 20
        total_width = len(items) * card_width + (len(items) - 1) * gap
        start_x = (720 - total_width) / 2  # center on 720pt wide slide

        for i, (label, value) in enumerate(items):
            card_id = f"{slide_id}_card_{i}"
            val_id = f"{slide_id}_val_{i}"
            lbl_id = f"{slide_id}_lbl_{i}"
            x = start_x + i * (card_width + gap)

            self._requests.extend([
                # Card background
                {"createShape": {
                    "objectId": card_id,
                    "shapeType": "ROUND_RECTANGLE",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {"width": self._pt(card_width), "height": self._pt(120)},
                        "transform": {
                            "scaleX": 1, "scaleY": 1,
                            "translateX": int(x * 12700), "translateY": 1800000,
                            "unit": "EMU",
                        },
                    },
                }},
                {"updateShapeProperties": {
                    "objectId": card_id,
                    "shapeProperties": {
                        "shapeBackgroundFill": {
                            "solidFill": {"color": {"rgbColor": BRAND["light_gray"]}}
                        },
                        "outline": {"outlineFill": {
                            "solidFill": {"color": {"rgbColor": BRAND["light_gray"]}}
                        }},
                    },
                    "fields": "shapeBackgroundFill,outline",
                }},
                # Value (big number)
                {"createShape": {
                    "objectId": val_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {"width": self._pt(card_width - 10), "height": self._pt(50)},
                        "transform": {
                            "scaleX": 1, "scaleY": 1,
                            "translateX": int((x + 5) * 12700), "translateY": 1950000,
                            "unit": "EMU",
                        },
                    },
                }},
                {"insertText": {"objectId": val_id, "text": str(value), "insertionIndex": 0}},
                {"updateTextStyle": {
                    "objectId": val_id,
                    "style": self._text_style(32, bold=True, color=BRAND["purple_dark"]),
                    "fields": "fontSize,fontFamily,bold,foregroundColor",
                }},
                {"updateParagraphStyle": {
                    "objectId": val_id,
                    "style": {"alignment": "CENTER"},
                    "fields": "alignment",
                }},
                # Label
                {"createShape": {
                    "objectId": lbl_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {"width": self._pt(card_width - 10), "height": self._pt(30)},
                        "transform": {
                            "scaleX": 1, "scaleY": 1,
                            "translateX": int((x + 5) * 12700), "translateY": 2700000,
                            "unit": "EMU",
                        },
                    },
                }},
                {"insertText": {"objectId": lbl_id, "text": label, "insertionIndex": 0}},
                {"updateTextStyle": {
                    "objectId": lbl_id,
                    "style": self._text_style(12, color=BRAND["dark_text"]),
                    "fields": "fontSize,fontFamily,foregroundColor",
                }},
                {"updateParagraphStyle": {
                    "objectId": lbl_id,
                    "style": {"alignment": "CENTER"},
                    "fields": "alignment",
                }},
            ])

        return slide_id

    def add_table_slide(self, title, headers, rows):
        """Add a slide with a data table.
        headers: list of column names
        rows: list of lists
        """
        slide_id = self._new_slide_id()
        title_id = f"{slide_id}_title"
        table_id = f"{slide_id}_table"
        num_rows = len(rows) + 1  # +1 for header
        num_cols = len(headers)

        self._requests.extend([
            {"createSlide": {
                "objectId": slide_id,
                "insertionIndex": self._slide_count - 1,
                "slideLayoutReference": {"predefinedLayout": "BLANK"},
            }},
            # Title
            {"createShape": {
                "objectId": title_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {"width": self._pt(650), "height": self._pt(50)},
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": 457200, "translateY": 274638,
                        "unit": "EMU",
                    },
                },
            }},
            {"insertText": {"objectId": title_id, "text": title, "insertionIndex": 0}},
            {"updateTextStyle": {
                "objectId": title_id,
                "style": self._text_style(28, bold=True, color=BRAND["purple_dark"]),
                "fields": "fontSize,fontFamily,bold,foregroundColor",
            }},
            # Table
            {"createTable": {
                "objectId": table_id,
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {"width": self._pt(650), "height": self._pt(300)},
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": 457200, "translateY": 1200000,
                        "unit": "EMU",
                    },
                },
                "rows": num_rows,
                "columns": num_cols,
            }},
        ])

        # Fill header row
        for col, header in enumerate(headers):
            self._requests.append({
                "insertText": {
                    "objectId": table_id,
                    "cellLocation": {"rowIndex": 0, "columnIndex": col},
                    "text": str(header),
                    "insertionIndex": 0,
                }
            })

        # Fill data rows
        for row_idx, row in enumerate(rows):
            for col_idx, cell in enumerate(row):
                self._requests.append({
                    "insertText": {
                        "objectId": table_id,
                        "cellLocation": {"rowIndex": row_idx + 1, "columnIndex": col_idx},
                        "text": str(cell),
                        "insertionIndex": 0,
                    }
                })

        # Style header row with purple background
        for col in range(num_cols):
            self._requests.append({
                "updateTableCellProperties": {
                    "objectId": table_id,
                    "tableRange": {
                        "location": {"rowIndex": 0, "columnIndex": col},
                        "rowSpan": 1, "columnSpan": 1,
                    },
                    "tableCellProperties": {
                        "tableCellBackgroundFill": {
                            "solidFill": {"color": {"rgbColor": BRAND["purple_dark"]}}
                        }
                    },
                    "fields": "tableCellBackgroundFill",
                }
            })

        return slide_id

    def add_insight_slide(self, title, bullets):
        """Add a slide with bullet-point insights."""
        slide_id = self._new_slide_id()
        title_id = f"{slide_id}_title"
        body_id = f"{slide_id}_body"
        text = "\n".join(f"• {b}" for b in bullets)

        self._requests.extend([
            {"createSlide": {
                "objectId": slide_id,
                "insertionIndex": self._slide_count - 1,
                "slideLayoutReference": {"predefinedLayout": "BLANK"},
            }},
            {"createShape": {
                "objectId": title_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {"width": self._pt(650), "height": self._pt(50)},
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": 457200, "translateY": 274638,
                        "unit": "EMU",
                    },
                },
            }},
            {"insertText": {"objectId": title_id, "text": title, "insertionIndex": 0}},
            {"updateTextStyle": {
                "objectId": title_id,
                "style": self._text_style(28, bold=True, color=BRAND["purple_dark"]),
                "fields": "fontSize,fontFamily,bold,foregroundColor",
            }},
            {"createShape": {
                "objectId": body_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {"width": self._pt(620), "height": self._pt(320)},
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": 640000, "translateY": 1200000,
                        "unit": "EMU",
                    },
                },
            }},
            {"insertText": {"objectId": body_id, "text": text, "insertionIndex": 0}},
            {"updateTextStyle": {
                "objectId": body_id,
                "style": self._text_style(16, color=BRAND["dark_text"]),
                "fields": "fontSize,fontFamily,foregroundColor",
            }},
        ])
        return slide_id

    def add_text_slide(self, title, body_text):
        """Add a simple text slide."""
        slide_id = self._new_slide_id()
        title_id = f"{slide_id}_title"
        body_id = f"{slide_id}_body"

        self._requests.extend([
            {"createSlide": {
                "objectId": slide_id,
                "insertionIndex": self._slide_count - 1,
                "slideLayoutReference": {"predefinedLayout": "BLANK"},
            }},
            {"createShape": {
                "objectId": title_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {"width": self._pt(650), "height": self._pt(50)},
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": 457200, "translateY": 274638,
                        "unit": "EMU",
                    },
                },
            }},
            {"insertText": {"objectId": title_id, "text": title, "insertionIndex": 0}},
            {"updateTextStyle": {
                "objectId": title_id,
                "style": self._text_style(28, bold=True, color=BRAND["purple_dark"]),
                "fields": "fontSize,fontFamily,bold,foregroundColor",
            }},
            {"createShape": {
                "objectId": body_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {"width": self._pt(620), "height": self._pt(320)},
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": 640000, "translateY": 1200000,
                        "unit": "EMU",
                    },
                },
            }},
            {"insertText": {"objectId": body_id, "text": body_text, "insertionIndex": 0}},
            {"updateTextStyle": {
                "objectId": body_id,
                "style": self._text_style(14, color=BRAND["dark_text"]),
                "fields": "fontSize,fontFamily,foregroundColor",
            }},
        ])
        return slide_id

    def publish(self, move_to_folder=None):
        """Send all queued requests and return the presentation URL."""
        if self._requests:
            url = f"{self.BASE}/{self._presentation_id}:batchUpdate"
            _api("POST", url, {"requests": self._requests}, self.token)
            self._requests = []

        # Optionally move to a specific Drive folder
        if move_to_folder:
            drive_url = (
                f"https://www.googleapis.com/drive/v3/files/{self._presentation_id}"
                f"?addParents={move_to_folder}&fields=id,parents"
            )
            _api("PATCH", drive_url, {}, self.token)

        link = f"https://docs.google.com/presentation/d/{self._presentation_id}/edit"
        print(f"\nPresentation ready: {link}")
        return link


if __name__ == "__main__":
    # Demo: create a sample deck
    deck = SlideDeck(f"Demo Deck — {datetime.now().strftime('%B %d, %Y')}")

    deck.add_title_slide(
        "Nalley Lexus Galleria",
        "Quarterly Business Review — Q1 2026"
    )

    deck.add_metrics_slide("Key Performance Metrics", {
        "VDP Views": "12,450",
        "Leads": "342",
        "SRP→VDP": "3.7%",
        "Avg Rating": "4.6★",
    })

    deck.add_table_slide(
        "Price Badge Distribution",
        ["Badge", "Count", "% of Inventory"],
        [
            ["Great", "28", "33%"],
            ["Good", "35", "41%"],
            ["Fair", "15", "18%"],
            ["No Badge", "7", "8%"],
        ]
    )

    deck.add_insight_slide("Key Insights", [
        "VDP views up 15% month-over-month driven by improved merchandising",
        "Price badge distribution shifted: 74% now at Good or Great (was 65%)",
        "SRP→VDP conversion rate of 3.7% exceeds group average of 3.1%",
        "Review volume on track for DealerRater award eligibility",
    ])

    url = deck.publish()
