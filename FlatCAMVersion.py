import logging

version = {
    "number": 8.5,
    "date": (2016, 7, 1),  # Year, Month, Day
    "name": None,
    "release": True,
}


def setup(app):
    app.version = version["number"]
    app.version_date = version["date"]
    if version["release"]:
        app.log.setLevel(logging.WARNING)
    else:
        app.log.setLevel(logging.DEBUG)

    if version["name"] is None and version["release"] == False:
        app.version_name = "Development Version"
    else:
        app.version_name = version["name"]
