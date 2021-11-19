#!/usr/bin/env python

"""

Batch rename tv show episodes

- Episodes should be stored in the following way:

    .../Show Name/Season 1/Episode 3

- Episodes must already be in the proper order
- Season Folders should contain 1 number that denotes the season

"""

from dataclasses import dataclass
import os
import argparse
import re
from typing import List


PREVIEW_MSG = "\n*** PREVIEW -- NO CHANGES HAVE BEEN MADE ***"


def get_extension(filename):
    """
    Extract file extension from filename using regex.

    Args:
        filename (str): name of file

    Returns:
        str: the file extension
    """
    match = re.search(r"\.(?P<ext>[^.]+)$", filename)
    if match:
        return match.group("ext")
    raise ValueError(f"No extension could be extracted from '{filename}'")


def remove_end_chars(text: str, char: str) -> str:
    """
    Recursively remove a specific trailing character until none are left.

    Args:
        text (str): text to be modified
        char (str): character to remove

    Returns:
        str: the original text with all of the characters removed from the end
    """
    if len(char) != 1:
        raise ValueError(f"char to be removed must only be 1 character, not {len(char)}")

    if text[-1] == char:
        text = text[:-1]
        return remove_end_chars(text, char)
    return text


class TVShow:
    """TV Show"""

    def __init__(self, path, custom_text="", ignore_files=None, ignore_ext=None):
        self.path = str(os.path.abspath(path))
        self.ignore_files = ignore_files if ignore_files is not None else []
        self.ignore_ext = ignore_ext if ignore_ext is not None else []

        self.season_padding = "02"
        self.episode_padding = "02"

        if custom_text:
            custom_text = remove_end_chars(custom_text, ".") + "."

        self.episode_scheme = custom_text + "s{season}e{episode}.{extension}"
        self.seasons = self.get_seasons()

    def get_seasons(self):
        """
        Gets sorted list of TVSeason objects for a given TVShow.

        Returns:
            List[TVSeason]: all of the season objects
        """

        seasons = []
        for folder in os.listdir(self.path):
            folder_path = os.path.join(self.path, folder)
            if (
                os.path.isdir(folder_path)
                and folder not in self.ignore_files
                and folder_path not in self.ignore_files
            ):
                seasons.append(TVSeason(self, folder_path))
        return sorted(seasons, key=lambda s: s.number)


class TVSeason:
    """TV Show Season"""

    def __init__(self, show: TVShow, path):
        """
        Init Season

        Args:
            show (Show): show object that Season is part of
            path (str): path to the season folder
            ignore_files (List[str]), optional): filenames to ignore.
                                                 Defaults to None.
            ignore_ext (List[str]), optional): file extensions to ignore.
                                               Defaults to None.
        """
        self.show = show
        self.path = os.path.normpath(path)
        self.name = self.get_name()
        self.number = self.get_season_number()
        self.episodes = self.get_episodes()

    def get_name(self):
        """
        Get the season folder name from path

        Raises:
            ValueError: if self.path isn't a str

        Returns:
            str: name of season folder
        """
        if isinstance(self.path, str):
            return os.path.basename(self.path)
        raise ValueError(f"Error getting season name: {self.path}")

    def get_season_number(self):
        """
        Attempt to extract season number from a season folder name.

        Raises:
            ValueError: if more than one number or
                        no numbers are found in the folder name

        Returns:
            int: season number
        """

        # extract season number
        match = re.search(r"^\D*(?P<season>\d+)\D*$", self.name)
        if match:
            return int(match.group("season"))

        # determine error
        message = (
            f"Could not extract season from '{self.name}'\n"
            "Season folder must contain exactly 1 number"
        )
        numbers_found = re.findall(r"\d+", self.name)
        if len(numbers_found) > 1:
            raise ValueError(f"{message}\nMultiple numbers found: {numbers_found}")
        raise ValueError(f"{message}\nNo numbers found")

    def get_episodes(self):
        """
        Gets a list of TVEpisode objects for a given TVSeason.

        Raises:
            ValueError: if self.path isn't a str

        Returns:
            List[TVEpisode]: all of the episode objects
        """

        episodes = []
        episode_number = 1
        for file_name in os.listdir(self.path):
            file_path = os.path.join(self.path, file_name)

            if (
                os.path.isfile(file_path)
                and file_name not in self.show.ignore_files
                and file_path not in self.show.ignore_files
                and get_extension(file_name) not in self.show.ignore_ext
            ):
                episodes.append(TVEpisode(self, file_path, episode_number))
                episode_number += 1

        return episodes


class TVEpisode:
    """TV Show Episode"""

    def __init__(self, season: TVSeason, path, number):
        self.season = season
        self.number = number
        self.old_path = path
        self.old_name = os.path.basename(path)
        self.new_name = self.season.show.episode_scheme.format(
            season=f"{self.season.number:{self.season.show.season_padding}}",
            episode=f"{self.number:{self.season.show.episode_padding}}",
            extension=get_extension(self.old_path),
        )
        self.new_path = os.path.join(self.season.path, self.new_name)

    def rename(self):
        pass


def print_actions(seasons: List[dict]) -> None:
    """
    Print a formatted list of all of the renaming actions that will occur.

    Args:
        seasons (List[dict]): list of season dicts
    """
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
        print(f" Season {season['num']} | {season['path']} | {len(season['actions'])} episodes")
        print(f"{'#' * total_width}")
        print(f"\n{'Current File Name:':{old_width}}{' ' * len(separator)}New File Name:")
        for action in season["actions"]:
            print(
                f"{os.path.basename(action['old']):{old_width}}"
                f"{separator}"
                f"{os.path.basename(action['new']):{new_width}}"
            )


def get_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: parsed arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", help="full path to top level show folder", required=True)
    parser.add_argument(
        "--scheme",
        help="name scheme to apply to beginning of all files after renaming",
        required=True,
    )
    parser.add_argument("--title_regex", help="regular expression to extract original episode name")
    parser.add_argument(
        "--ignore",
        help="files and folders that should be ignored",
        nargs="+",
        default=[],
    )
    parser.add_argument(
        "--non_media",
        help="file extensions that should be ignored",
        nargs="+",
        default=["nfo", "txt"],
    )
    parser.add_argument("-e", "--execute", help="actually make the changes", action="store_true")
    return parser.parse_args()


def main():
    """Main."""

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

    for season in seasons:
        print(f"  [S{season['num']:{season_padding}}] - \"{season['name']}\"")

    if args.ignore:
        print(f"\nIgnoring {len(args.ignore)} files and folders:")
        for folder in args.ignore:
            print(f"  {folder}")

    if args.non_media:
        print("\nIgnoring all files with these extensions:")
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
