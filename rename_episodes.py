#!/usr/bin/env python

# Batch rename files

# this script assumes the episodes are stored in the following way:
# .../Show Name/Season 1/Episode 3
# episodes must already be in the proper order *

import os
import argparse
import re
import pprint as pp


PREVIEW_MSG = "\n*** PREVIEW -- NO CHANGES HAVE BEEN MADE ***"


def remove_end_chars(text, char):
    if text[-1] == char:
        text = text[:-1]
        return remove_end_chars(text, char)
    else:
        return text


def get_season_number(text):
    match = re.search(r"^\D*(?P<season>\d+)\D*$", text)
    if match:
        return int(match.group("season"))
    else:
        message = f'\n\nCould not extract season: "{text}"\nSeason folder must contain exactly 1 number'
        numbers_found = re.findall(r"\d+", text)
        if len(numbers_found) > 1:
            raise ValueError(f"{message}\nMultiple numbers found: {numbers_found}")
        else:
            raise ValueError(f"{message}\nNo numbers found")


def get_extension(filename):
    return re.search(r"\.(?P<ext>[^.]+)$", filename).group("ext")


def get_episodes(path, non_media):
    return [
        file
        for file in os.listdir(path)
        if os.path.isfile(f"{path}/{file}") and get_extension(file) not in non_media
    ]


def print_actions(seasons):
    print("\nFiles to rename:")
    old_width = max(
        [
            max([len(os.path.basename(action["old"])) for action in season["actions"]])
            for season in seasons
        ]
    )
    new_width = max(
        [
            max([len(os.path.basename(action["new"])) for action in season["actions"]])
            for season in seasons
        ]
    )
    separator = "  -->  "
    total_width = old_width + new_width + len(separator)

    for season in seasons:
        print(f"\n{'#' * total_width}")
        print(
            f" Season {season['num']} | {season['path']} | {len(season['actions'])} episodes"
        )
        print(f"{'#' * total_width}")
        print(
            f"\n{'Current File Name:':{old_width}}{' ' * len(separator)}New File Name:"
        )
        for action in season["actions"]:
            print(
                f"{os.path.basename(action['old']):{old_width}}{separator}{os.path.basename(action['new']):{new_width}}"
            )


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path", help="full path to top level show folder", required=True
    )
    parser.add_argument(
        "--scheme",
        help="name scheme to apply to beginning of all files after renaming",
        required=True,
    )
    parser.add_argument(
        "--title_regex", help="regular expression to extract original episode name"
    )
    parser.add_argument(
        "--ignore", help="folders that should be ignored", nargs="+", default=[]
    )
    parser.add_argument(
        "-e", "--execute", help="actually make the changes", action="store_true"
    )
    parser.add_argument(
        "--non_media",
        help="file extensions that aren't episodes",
        default=["nfo", "txt"],
    )
    return parser.parse_args()


def main():

    # get command-line arguments
    args = get_args()

    if not args.execute:
        print(PREVIEW_MSG)

    # remove slashes at end of path if it contains any
    args.path = remove_end_chars(args.path, "/")
    # remove dots at end of name scheme if it contains any
    args.scheme = remove_end_chars(args.scheme, ".")

    # organize all the season folders; ignore stray files and excluded folders
    folders = [
        folder
        for folder in os.listdir(args.path)
        if os.path.isdir(f"{args.path}/{folder}") and folder not in args.ignore
    ]
    seasons = [
        {
            "num": get_season_number(folder),
            "name": folder,
            "path": f"{args.path}/{folder}",
        }
        for folder in sorted(folders, key=get_season_number)
    ]

    # determine zero-padding
    season_counts = [s["num"] for s in seasons]
    season_max_digits = len(str(max(season_counts)))
    season_padding = f"0{season_max_digits}" if season_max_digits > 2 else "02"

    episode_counts = [len(get_episodes(s["path"], args.non_media)) for s in seasons]
    episode_max_digits = len(str(max(episode_counts)))
    episode_padding = f"0{episode_max_digits}" if episode_max_digits > 2 else "02"

    # print info about which folders will be affected
    print(f"\nFound {len(seasons)} season(s) in the following order:")
    for s in seasons:
        print(f"  [S{s['num']:{season_padding}}] - \"{s['name']}\"")
    if args.ignore:
        print(f"\nIgnoring {len(args.ignore)} folder(s):")
        for f in args.ignore:
            print(f"  {f}")
    print("\nIgnoring files with these extensions:")
    for ext in args.non_media:
        print(f"  .{ext}")

    # naming scheme
    episode_scheme = "{scheme}.S{season}E{episode}.{extension}"
    print("\nNew episode naming scheme:")
    print(
        episode_scheme.format(
            scheme=args.scheme,
            season=f"{0:{season_padding}}",
            episode=f"{0:{episode_padding}}",
            extension="<extension>",
        )
    )

    # loop through seasons and compile actions to perform
    for season in seasons:

        # list of renaming actions to do
        season["actions"] = []

        # get all the episode files and loop through them
        episodes = get_episodes(season["path"], args.non_media)
        if not episodes:
            raise ValueError(
                f"\n\n{season['path']} contains no episodes!"
                "\nDelete folder or add to ignore list."
            )
        for i, old_episode_name in enumerate(episodes):

            episode_number = i + 1
            old_episode_path = f"{season['path']}/{old_episode_name}"

            # generate new name
            new_episode_name = episode_scheme.format(
                scheme=args.scheme,
                season=f"{season['num']:{season_padding}}",
                episode=f"{episode_number:{episode_padding}}",
                extension=get_extension(old_episode_path),
            )
            new_episode_path = f"{season['path']}/{new_episode_name}"

            # append renaming action
            season["actions"].append({"old": old_episode_path, "new": new_episode_path})

    # print a preview of actions
    print_actions(seasons)

    # do all of the renaming
    if args.execute:
        total_episodes = sum(episode_counts)
        response = input(
            f"\nRename {total_episodes} episodes? This action cannot be undone. (yes/no): "
        )
        if response.lower() == "yes":
            for season in seasons:
                for action in season["actions"]:
                    os.rename(action["old"], action["new"])
            print(f"{total_episodes} files renamed.")
    else:
        print(PREVIEW_MSG)


if __name__ == "__main__":
    main()
