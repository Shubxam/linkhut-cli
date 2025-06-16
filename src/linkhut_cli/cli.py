#!/usr/bin/env python3
"""
LinkHut CLI - Command-line interface for managing bookmarks with LinkHut.

This module implements the CLI commands and argument parsing for the LinkHut CLI
application, using the Typer library. It provides commands for managing bookmarks
and tags, checking configuration status, and handling user input.
"""

import os
import sys

import dotenv
import typer

# Add the parent directory to sys.path to be able to import from linkhut_lib
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from linkhut_lib.linkhut_lib import (
    create_bookmark,
    delete_bookmark,
    delete_tag,
    get_bookmarks,
    get_reading_list,
    reading_list_toggle,
    rename_tag,
    update_bookmark,
)

from .utils import parse_bulk_items

app = typer.Typer(help="LinkHut CLI - Manage your bookmarks from the command line")
bookmarks_app = typer.Typer(help="Manage bookmarks")
tags_app = typer.Typer(help="Manage tags")
app.add_typer(bookmarks_app, name="bookmarks")
app.add_typer(tags_app, name="tags")


# Check environment variables on startup
def check_env_variables():
    """Check if required environment variables are set.

    This function loads environment variables from a .env file if present,
    then checks if the required API credentials are set. If any are missing,
    it displays an error message with instructions.

    Returns:
        bool: True if all required environment variables are set, False otherwise
    """
    dotenv.load_dotenv()
    missing: list[str] = []
    if not os.getenv("LH_PAT"):
        missing.append("LH_PAT")
    if not os.getenv("LINK_PREVIEW_API_KEY"):
        missing.append("LINK_PREVIEW_API_KEY")

    if missing:
        typer.secho(
            f"Error: Missing required environment variables: {', '.join(missing)}", fg="red"
        )
        typer.secho("Please add them to your .env file or set them in your environment", fg="red")
        return False
    return True


@app.command()
def config_status():
    """Check authentication configuration status.

    This command displays the current configuration status of the CLI,
    including whether the required API tokens are set and showing masked
    versions of the tokens for verification.

    Returns:
        None: Results are printed directly to stdout
    """
    dotenv.load_dotenv()
    lh_pat = os.getenv("LH_PAT")
    lp_api_key = os.getenv("LINK_PREVIEW_API_KEY")

    typer.echo("Configuration status:")

    if lh_pat:
        typer.secho("✅ LinkHut API Token is configured", fg="green")
        # Show the first few and last few characters of the token
        masked = lh_pat[:4] + "*" * (len(lh_pat) - 8) + lh_pat[-4:] if len(lh_pat) > 8 else "****"
        typer.echo(f"   Token: {masked}")
    else:
        typer.secho("❌ LinkHut API Token is not configured", fg="red")

    if lp_api_key:
        typer.secho("✅ Link Preview API Key is configured", fg="green")
        masked = (
            lp_api_key[:4] + "*" * (len(lp_api_key) - 8) + lp_api_key[-4:]
            if len(lp_api_key) > 8
            else "****"
        )
        typer.echo(f"   API Key: {masked}")
    else:
        typer.secho("❌ Link Preview API Key is not configured", fg="red")


# Bookmark commands
@bookmarks_app.command("get")
def list_bookmarks(
    tag: str = typer.Option(
        "", "--tag", "-g", help="Filter by one tag or multiple tags (comma-separated or space-separated inside quotes)"
    ),
    count: int = typer.Option(0, "--count", "-c", help="Number most recent bookmarks to show, can also be used with one tag"),
    date: str = typer.Option(
        "", "--date", "-d", help="Date to filter bookmarks(in YYYY-MM-DD format)"
    ),
    url: str = typer.Option("", "--url", "-u", help="URL to filter bookmarks"),
):
    """Get bookmarks from your LinkHut account.

    This command retrieves and displays bookmarks from your LinkHut account.\n
    You can filter the results by tags, date, or specific URL, and limit the
    number of results returned.

    If count is provided, it fetches the most recent 'count' bookmarks.
    If other filters are applied without count, it uses the filtering API.
    Without any arguments, it returns the 15 most recent bookmarks.
    """
    if not check_env_variables():
        return

    params: dict[str, str | int] = {}

    if count:
        params["count"] = count
        if tag:
            # Only take the first tag
            # tags_list = parse_bulk_items(content=tag, type="tag")
            tags = sanitize_tags(tag)
            params["tag"] = tags
            if len(tags.split()) > 1:
                typer.echo(f"Multiple tags detected, only the first tag: {tags.split()[0]} will be used.")

    elif tag or date or url:
        # whitespace or comma separated string
        if tag:
            params["tag"] = sanitize_tags(tag)

        if date:
            params["date"] = date

        if url:
            params["url"] = url

    fetched_bookmarks: list[dict[str, str]] = get_bookmarks(**params)

    if fetched_bookmarks[0].get("error") == "invalid_date_format":  # dateformat error
        typer.echo("Invalid date format. Please use YYYY-MM-DD format.")
        return
    elif fetched_bookmarks[0].get("error") == "invalid_url_format":  # url format error
        typer.echo("Invalid URL format. Please provide a valid URL.")
        return
    elif fetched_bookmarks[0].get("error") == "no_bookmarks_found":  # no bookmarks found
        typer.echo("No bookmarks found with the given filters.")
        return
    elif fetched_bookmarks[0].get("error"):
        typer.echo("An error occurred while fetching bookmarks. Issue with network or API.")
        return

    for i, bookmark in enumerate(fetched_bookmarks, 1):

        title: str = bookmark.get("description", "No title available")
        href: str = bookmark.get("href", "No URL")
        tags: str = bookmark.get("tags", "").replace(" ", ", ")
        is_private: bool = bookmark.get("shared") == "no"
        to_read: bool = bookmark.get("toread") == "yes"
        note: str = bookmark.get("extended", "")
        date_str: str = bookmark.get("time", "No date available")

        # Format output with color and indicators
        title_color: str = "bright_white" if to_read else "white"
        privacy: str = "[private]" if is_private else "[public]"
        read_status: str = "[unread]" if to_read else ""
        status_text: str = f"{privacy} {read_status}"
        date_str: str = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").strftime("%d %B %Y - %I:%M %p")

        typer.secho(f"{i}. {title}", fg=title_color, bold=to_read)
        typer.secho(f"   URL: {href}", fg="blue")
        typer.secho(f"   Tags: {tags}", fg="cyan")
        typer.secho(f"   Date: {date_str}", fg="magenta")
        typer.secho(f"   Status: {status_text}", fg="yellow")
        typer.echo("")  # Empty line between bookmarks
        if note:
            typer.secho(f"   Note: {note}", fg="green")


# todo: #25 remove the bulk argument from add_bookmark and infer if multiple URLs are provided by checking for newlines or commas
@bookmarks_app.command("add")
def add_bookmark(
    url: str = typer.Argument(..., help="URL of the bookmark, must start with http:// or https://"),
    bulk: bool = typer.Option(False, "--bulk", "-b", help="Add multiple bookmarks [inside quotes, separated by newlines or commas]"),
    title: str = typer.Option("", "--title", "-t", help="Title of the bookmark"),
    note: str = typer.Option("", "--note", "-n", help="Note for the bookmark"),
    tags: str = typer.Option("", "--tag", "-g", help="Tags to associate with the bookmark [for multiple tags, use space or comma separated values inside quotes]"),
    private: bool = typer.Option(False, "--private", "-p", help="Make the bookmark private"),
    to_read: bool = typer.Option(False, "--to-read", "-r", help="Add to reading list"),
    replace: bool = typer.Option(False, "--replace", "-R", help="Replace existing bookmark with the same URL")
) -> None:
    """Add a new bookmark to your LinkHut account.

    This command creates a new bookmark with the specified URL and optional metadata.
    If a title is not provided, it will attempt to fetch it automatically.
    If tags are not provided, it will attempt to suggest tags based on the content.

    The bookmark can be marked as private or public, and can be added to your reading list.
    """
    
    if not check_env_variables():
        return
    
    if bulk:
        add_bulk_bookmarks(urls=url, note=note, tags=tags, private=private, to_read=to_read, replace=replace)
        typer.secho("All bookmarks processed successfully!", fg="green")
        return

    fields_dict: dict[str, str] = create_bookmark(
        url=url, title=title, note=note, tags=tags, private=private, to_read=to_read
    )

    if fields_dict.get("error") == "invalid_url":
        typer.secho(f"\nInvalid URL: {url}", fg="red")
        typer.secho("Please provide a valid URL starting with http:// or https://", fg="red")
        return
    
    elif fields_dict.get("error") == "bookmark_exists":
        typer.secho(f"\nBookmark with URL '{url}' already exists.", fg="yellow")
        return
    
    elif fields_dict.get("error"):
        typer.secho("\nError creating bookmark: API/network issue.", fg="red")
        return
    else:
        typer.secho("\nBookmark created successfully!", fg="green")
        typer.secho(f"Title: {fields_dict.get('description')}", fg="bright_white", bold=True)
        typer.echo(f"URL: {fields_dict.get('url')}")
        typer.echo(f"Tags: {fields_dict.get('tags', '').replace('+', ', ')}")  # while sending http request, tags are seperated by +, so replace + with ', '
        typer.echo(f"Privacy: {'Private' if fields_dict.get('shared') == 'no' else 'Public'}")
        if fields_dict.get("toread") == "yes":
            typer.echo("Added to reading list")
        if fields_dict.get("extended"):
            typer.echo(f"Note: {fields_dict.get('extended')}")
        

def add_bulk_bookmarks(urls: str, note: str, tags: str, private: bool, to_read: bool = False, replace: bool = False) -> None:
    """Add multiple bookmarks to your LinkHut account.

    This function takes a string of URLs separated by newlines or commas and
    adds them as bookmarks. It also allows for optional metadata like notes,
    tags, and privacy settings.

    Args:
        urls (str): A string containing URLs separated by newlines or commas.
        note (str): Note to associate with the bookmarks.
        tags (str): Tags to associate with the bookmarks.
        private (bool): Whether to make the bookmarks private.

    Returns:
        None: Results are printed directly to stdout
    """

    urls_list: list[str] = parse_bulk_items(content=urls)
    typer.echo(f"Found {len(urls_list)} URLs to add:")
    for url in tqdm(urls_list, desc="Adding bookmarks", unit="bookmark", ncols=80):
        add_bookmark(url=url, title="", note=note, tags=tags, private=private, bulk=False, to_read=to_read, replace=replace)
        typer.echo("-" * 40)
        time.sleep(1)  # Sleep for 1 second to avoid hitting API rate limits


@bookmarks_app.command("update")
def update_bookmark_cmd(
    url: str = typer.Argument(..., help="URL of the bookmark to update"),
    tags: str = typer.Option("", "--tag", "-g", help="New tags for the bookmark"),
    note: str = typer.Option("", "--note", "-n", help="Note to append to the bookmark"),
    private: bool = typer.Option(False, "--private/--public", help="Update bookmark privacy"),
    replace: bool = typer.Option(False, "--replace", "-R", help="Replace existing bookmark with the same URL. Default is False which appends the new tags and note to the existing bookmark"),
):
    """Update an existing bookmark in your LinkHut account.

    This command updates a bookmark identified by its URL. 
    You can change the tags, append a note to any existing notes, and update the privacy setting.

    If no bookmark with the specified URL exists, a new one will be created.
    """
    if not check_env_variables():
        return

    private_str: str = "yes" if private else "no"
    tags_str: str = tags
    result: dict[str, str] = update_bookmark(url=url, new_tag=tags_str, new_note=note or "", new_private=private_str, replace=replace)

    if result.get("status") == "missing_update_parameters":
        typer.secho("No update parameters provided. Please specify at least one parameter to update.", fg="red")
        return
    elif result.get("status") == "no_update_needed":
        typer.secho("No changes detected. Bookmark is already up to date.", fg="yellow")
        return
    elif result.get("error") == "invalid_url_format":
        typer.secho(f"Invalid URL format: {url}. Please provide a valid URL.", fg="red")
        return
    elif result.get("error"):
        typer.secho("Error updating bookmark: API/network issue.")
    else:
        if result.get("status") == "no_bookmark_found":
            typer.secho(f"No bookmark found with URL: {url}. Creating a new bookmark.", fg="yellow")
        
        typer.secho("Operation Success!", fg="green")
        typer.secho(f"Title: {result.get('description')}", fg="bright_white", bold=True)
        typer.echo(f"URL: {result.get('url')}")
        typer.echo(f"Tags: {result.get('tags', '').replace('+', ', ')}")  # while sending http request, tags are seperated by +, so replace + with ', '
        typer.echo(f"Privacy: {'Private' if result.get('shared') == 'no' else 'Public'}")
        if result.get("toread") == "yes":
            typer.echo("Added to reading list")
        if result.get("extended"):
            typer.echo(f"Note: {result.get('extended')}")


# todo: evaluate the need for try except block in cli
# todo: configure required arguments and position only arguments
@bookmarks_app.command("delete")
def delete_bookmark_cmd(
    url: str = typer.Argument(..., help="URL of the bookmark to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Delete without confirmation"),
):
    """Delete a bookmark from your LinkHut account.

    This command deletes a bookmark identified by its URL. It first shows the bookmark
    details and then asks for confirmation before deleting. Use the --force option
    to skip the confirmation prompt.

    Returns:
        None: Results are printed directly to stdout
    """
    if not check_env_variables():
        return

    # First fetch the bookmark details to show the user what they're deleting
    bookmark: dict[str, str] = get_bookmarks(url=url)[0]

    if bookmark.get("error") == "no_bookmarks_found":
        typer.secho(f"❌ Bookmark with URL '{url}' not found.", fg="red")
        return
    elif bookmark.get("error"):
        typer.secho("❌ Error fetching bookmark details. Issue with network or API.", fg="red")
        return

    # Display bookmark details
    typer.secho("\nBookmark Details:", fg="bright_blue", bold=True)

    title = bookmark.get("description", "No title")
    bookmark_url = bookmark.get("href", "No URL found")
    tags_str = bookmark.get("tags", "").replace(" ", ", ")
    is_private = bookmark.get("shared") == "no"
    to_read = bookmark.get("toread") == "yes"
    note = bookmark.get("extended", "")

    typer.secho(f"Title: {title}", fg="bright_white", bold=True)
    typer.echo(f"URL: {bookmark_url}")
    typer.echo(f"Tags: {tags_str}")
    typer.echo(f"Privacy: {'Private' if is_private else 'Public'}")
    typer.echo(f"Read Status: {'To Read' if to_read else 'Read'}")

    if note:
        typer.echo(f"Note: {note}")

    typer.echo("")  # Empty line for spacing

    # Ask for confirmation unless force flag is set
    if not force:
        confirmed = typer.confirm("Are you sure you want to delete this bookmark?")
        if not confirmed:
            typer.echo("Operation cancelled.")
            return

    result = delete_bookmark(url=url)

    if result.get("bookmark_deletion") == "success":
        typer.secho("✅ Bookmark deleted successfully!", fg="green")
    else:
        typer.secho("❌ Failed to delete bookmark.", fg="red")


# Tag commands
@tags_app.command("rename")
def rename_tag_cmd(
    old_tag: str = typer.Argument(..., help="Current tag name"),
    new_tag: str = typer.Argument(..., help="New tag name"),
):
    """Rename a tag across all bookmarks.

    This command renames a tag across all your bookmarks, changing all instances
    of the old tag to the new tag name. This is useful for correcting typos or
    standardizing your tag naming conventions.

    Args:
        old_tag: The current tag name to be replaced
        new_tag: The new tag name to use instead

    Returns:
        None: Results are printed directly to stdout
    """
    if not check_env_variables():
        return

    try:
        success = rename_tag(old_tag=old_tag, new_tag=new_tag)

        if success:
            typer.secho(f"✅ Tag '{old_tag}' renamed to '{new_tag}' successfully!", fg="green")
        else:
            typer.secho(f"❌ Failed to rename tag '{old_tag}'.", fg="red")

    except Exception as e:
        typer.secho(f"Error renaming tag: {e}", fg="red", err=True)
        raise typer.Exit(code=1) from e


@tags_app.command("delete")
def delete_tag_cmd(
    tag: str = typer.Argument(..., help="Tag to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Delete without confirmation"),
):
    """Delete a tag from all bookmarks.

    This command removes a specified tag from all your bookmarks. By default, it will ask for confirmation before deleting. Use the --force option to skip the confirmation prompt.

    Args:\n
        tag: The tag name to delete\n
        force: Whether to skip the confirmation prompt (default: False)
    """
    if not check_env_variables():
        return

    if not force:
        confirmed = typer.confirm(
            f"Are you sure you want to delete the tag '{tag}' from all bookmarks?"
        )
        if not confirmed:
            typer.echo("Operation cancelled.")
            return

    result: dict[str, str] = delete_tag(tag=tag)

    if result.get("error") == "invalid_tag_format":
        typer.secho(f"❌ Invalid tag format: '{tag}'. Tags must be alphanumeric and can contain underscores and hyphens, and be up to 50 characters long.", fg="red")
        return
    elif result.get("tag_deletion") == "success":
        typer.secho(f"✅ Tag '{tag}' deleted successfully from all bookmarks!", fg="green")
        return
    else:
        typer.secho(f"❌ Failed to delete tag '{tag}'. It might not exist or there was an issue with the API.", fg="red")
        return


# todo: update the output format for reading list command
@app.command("reading-list")
def reading_list_cmd(
    url: str = typer.Argument("", help="URL of the bookmark to add/remove from reading list"),
    count: int = typer.Option(5, "--count", "-c", help="Number of bookmarks to show"),
    to_read: bool = typer.Option(True, "--to-read/--read", help="Mark as read or to-read"),
    note: str = typer.Option("", "--note", "-n", help="Note to add"),
    tags: str = typer.Option("", "--tag", "-g", help="Tags to add if bookmark doesn't exist"),
):
    """Display your reading list or add/remove items from it.

    Without arguments, shows your reading list.
    With URL and flags, adds/removes items from reading list using update_bookmark.

    Examples:
        linkhut reading-list                                    # Show reading list
        linkhut reading-list --count 10                         # Show 10 items
        linkhut reading-list https://example.com --to-read      # Add to reading list
        linkhut reading-list https://example.com --read         # Mark as read
        linkhut reading-list https://example.com --to-read --note "Important" --tag python

    Args:
        url: URL to add/remove from reading list (optional)
        count: Number of bookmarks to show when displaying list
        to_read: Whether to mark as to-read (True) or read (False)
        note: Note to add when updating bookmark
        tags: Tags to add if bookmark doesn't exist
    """
    if not check_env_variables():
        return

    # If URL is provided, update the bookmark's reading status
    if url:
        result = update_bookmark(url=url, new_tag=tags, new_note=note, new_to_read=to_read)

        if result.get("error"):
            typer.secho(f"❌ Error updating reading list: {result.get('error')}", fg="red")
            return
        
        elif result.get("status") == "missing_update_parameters":
            typer.secho("❌ No update parameters provided. Please specify at least one parameter to update.", fg="red")
            return

        if result.get("status") == "no_bookmark_found":
            typer.secho(f"Item with URL '{url}' does not exist in reading list. Adding it now.", fg="yellow")
      
        action = "Added to" if to_read else "Removed from"

        typer.secho(f"✅ {action} reading list!", fg="green")
        typer.echo(f"URL: {url}")

        if tags:
            typer.echo(f"Tags: {result.get('tags', '').replace(' ', ', ')}")
        if note:
            typer.echo(f"Note: {result.get('extended', '')}")

        # Show a helpful tip for the next possible action
        if to_read:
            typer.echo("\nTip: View your reading list with 'linkhut reading-list'")
        else:
            typer.echo(f"\nTip: Add it back to your reading list with 'linkhut reading-list {url} --to-read'")
        return

    # If no URL provided, show the reading list
    try:
        reading_list: list[dict[str, str]] = get_reading_list(count=count)

        if reading_list[0].get("error") == "no_bookmarks_found":
            typer.echo("Your reading list is empty.")
            return
        elif reading_list[0].get("error") == "api_error":
            typer.secho("Error fetching reading list. Something went wrong with the API.", fg="red")
            return
        elif reading_list[0].get("error"):
            typer.secho(f"Error fetching reading list: {reading_list[0].get('error')}", fg="red")
            return

        for i, bookmark in enumerate(reading_list, 1):
            title: str = bookmark.get("description", "No title available")
            bookmark_url: str = bookmark.get("href", "")
            tags_list: list[str] = bookmark.get("tags", "").split(" ")
            note_str: str = bookmark.get("extended", "")
            private: bool = bookmark.get("shared") == "no"
            date_str: str = bookmark.get("time", "No date available")
            date_str: str = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").strftime("%d %B %Y - %I:%M %p GMT")

            typer.secho(f"{i}. {title}", fg="bright_white", bold=True)
            typer.echo(f"   URL: {bookmark_url}")
            typer.echo(f"   date added: {date_str}")
            typer.echo(f"   Private: {'Yes' if private else 'No'}")

            if tags_list and tags_list[0]:  # Check if tags exist and aren't empty
                tag_str: str = ", ".join(tags_list)
                typer.echo(f"   Tags: {tag_str}")

            if note_str:
                typer.echo(f"   Note: {note_str}")

            typer.echo("")  # Empty line between bookmarks
        typer.echo("\nTo mark as read: linkhut reading-list URL --read")
        typer.echo("To view details: linkhut bookmarks get --url URL")

    except Exception as e:
        typer.secho(f"Error fetching reading list: {e}", fg="red", err=True)
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
