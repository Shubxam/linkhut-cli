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
@bookmarks_app.command("list")
def list_bookmarks(
    tag: list[str] | None = typer.Option(
        None, "--tag", "-t", help="Filter by tags, will only take 1 tag is count is set"
    ),
    count: int | None = typer.Option(None, "--count", "-c", help="Number of bookmarks to show"),
    date: str | None = typer.Option(
        None, "--date", "-d", help="Date to filter bookmarks(in YYYY-MM-DD format)"
    ),
    url: str | None = typer.Option(None, "--url", "-u", help="URL to filter bookmarks"),
):
    """List bookmarks from your LinkHut account.

    This command retrieves and displays bookmarks from your LinkHut account.
    You can filter the results by tags, date, or specific URL, and limit the
    number of results returned.

    If count is provided, it fetches the most recent 'count' bookmarks.
    If other filters are applied without count, it uses the filtering API.
    Without any arguments, it returns the 15 most recent bookmarks.

    Returns:
        None: Results are printed directly to stdout
    """
    if not check_env_variables():
        return

    params = {}

    try:
        if count:
            params["count"] = count
            if tag:
                params["tag"] = [tag[0]]

        elif tag or date or url:
            params["tag"] = tag
            params["date"] = date
            params["url"] = url

        else:
            params["count"] = 15

        result, status_code = get_bookmarks(**params)  # pyright: ignore

        if status_code != 200 or not result or not result.get("posts"):
            typer.echo("No bookmarks found.")
            return

        posts = result.get("posts", [])
        typer.echo(f"Found {len(posts)} bookmarks:")

        for i, bookmark in enumerate(posts, 1):
            title: str = bookmark.get("description", "No title")
            url = bookmark.get("href", "")
            tags = bookmark.get("tags", "").split(",") if bookmark.get("tags") else []
            is_private = bookmark.get("shared") == "no"
            to_read = bookmark.get("toread") == "yes"

            # Format output with color and indicators
            title_color = "bright_white" if to_read else "white"
            privacy = "[Private]" if is_private else ""
            read_status = "[To Read]" if to_read else ""

            typer.secho(f"{i}. {title}", fg=title_color, bold=to_read)
            typer.echo(f"   URL: {url}")

            if tags and tags[0]:  # Check if tags exist and aren't empty
                tag_str = ", ".join(tags)
                typer.echo(f"   Tags: {tag_str}")

            if privacy or read_status:
                status_text = f"   Status: {privacy} {read_status}".strip()
                typer.echo(status_text)

            typer.echo("")  # Empty line between bookmarks

    except Exception as e:
        typer.secho(f"Error fetching bookmarks: {e}", fg="red", err=True)
        raise typer.Exit(code=1) from e


@bookmarks_app.command("add")
def add_bookmark(
    url: str = typer.Argument(..., help="URL of the bookmark, must start with http:// or https://"),
    bulk: bool = typer.Option(False, "--bulk", "-b", help="Add multiple bookmarks"),
    title: str = typer.Option("", "--title", "-t", help="Title of the bookmark"),
    note: str = typer.Option("", "--note", "-n", help="Note for the bookmark"),
    tags: str = typer.Option("", "--tag", "-g", help="Tags to associate with the bookmark"),
    private: bool = typer.Option(False, "--private", "-p", help="Make the bookmark private"),
    to_read: bool = typer.Option(False, "--to-read", "-r", help="Mark as to-read"),
) -> None:
    """Add a new bookmark to your LinkHut account.

    This command creates a new bookmark with the specified URL and optional metadata.
    If a title is not provided, it will attempt to fetch it automatically from the page.
    If tags are not provided, it will attempt to suggest tags based on the content.

    The bookmark can be marked as private or public, and can be added to your reading list.

    Returns:
        None: Results are printed directly to stdout
    """
    
    if not check_env_variables():
        return
    
    if bulk:
        add_bulk_bookmarks(urls=url, note=note, tags=tags, private=private)
        typer.secho("All bookmarks processed successfully!", fg="green")
        return None

    fields_dict = create_bookmark(
        url=url, title=title, note=note, tags=tags, private=private, to_read=to_read
    )

    if not fields_dict.get("status"):
        typer.secho("✅ Bookmark created successfully!", fg="green")
        typer.secho(f"Title: {fields_dict.get('description')}", fg="bright_white", bold=True)
        typer.echo(f"URL: {fields_dict.get('url')}")
        typer.echo(f"Tags: {fields_dict.get('tags', '').replace('+', ', ')}")  # in http request, tags are seperated by +, so replace + with ', '
        typer.echo(f"Privacy: {'Private' if fields_dict.get('shared') == 'no' else 'Public'}")
        typer.echo(f"Read Status: {'To Read' if fields_dict.get('toread') == 'yes' else 'Read'}")
        if fields_dict.get("extended"):
            typer.echo(f"Note: {fields_dict.get('extended')}")
    else:
        typer.secho(f"Error creating bookmark: {fields_dict.get('status')}", fg="yellow")
        

def add_bulk_bookmarks(urls: str, note: str, tags: str, private: bool, to_read: bool = False) -> None:
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
    # todo: add rate limiting
    urls_list: list[str] = parse_bulk_items(content=urls, type="url")
    typer.echo(f"Found {len(urls_list)} URLs to add:")
    for url in urls_list:
        add_bookmark(url=url, title="", note=note, tags=tags, private=private, bulk=False, to_read=to_read)


@bookmarks_app.command("update")
def update_bookmark_cmd(
    url: str = typer.Argument(..., help="URL of the bookmark to update"),
    tags: list[str] | None = typer.Option(None, "--tag", "-g", help="New tags for the bookmark"),
    note: str | None = typer.Option(None, "--note", "-n", help="Note to append to the bookmark"),
    private: bool | None = typer.Option(None, "--private/--public", help="Update bookmark privacy"),
):
    """Update an existing bookmark in your LinkHut account.

    This command updates a bookmark identified by its URL. You can change the tags,
    append a note to any existing notes, and update the privacy setting.

    If no bookmark with the specified URL exists, a new one will be created.

    Returns:
        None: Results are printed directly to stdout
    """
    if not check_env_variables():
        return

    try:
        success = update_bookmark(url=url, new_tag=tags, new_note=note, private=private)

        if success:
            typer.secho("✅ Bookmark updated successfully!", fg="green")
            typer.echo(f"URL: {url}")
            if tags:
                typer.echo(f"Updated tags: {', '.join(tags)}")
            if note:
                typer.echo("Note appended")
            if private is not None:
                status = "Private" if private else "Public"
                typer.echo(f"Updated visibility: {status}")
        else:
            typer.secho("❌ Failed to update bookmark.", fg="red")

    except Exception as e:
        typer.secho(f"Error updating bookmark: {e}", fg="red", err=True)
        raise typer.Exit(code=1) from e


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

    try:
        # First fetch the bookmark details to show the user what they're deleting
        bookmark_dict, status_code = get_bookmarks(url=url)

        if status_code != 200:
            typer.secho(f"❌ Bookmark with URL '{url}' not found.", fg="red")
            return

        # Extract bookmark details
        bookmark: list[dict[str, str]] | None = (
            bookmark_dict.get("posts")[0] if bookmark_dict.get("posts") else None
        )  # pyright: ignore

        if not bookmark:
            typer.secho(f"❌ Bookmark with URL '{url}' not found.", fg="red")
            return

        # Display bookmark details
        typer.secho("\nBookmark Details:", fg="bright_blue", bold=True)

        title = bookmark.get("description", "No title")
        bookmark_url = bookmark.get("href", "")
        tags = bookmark.get("tags", "").split(",") if bookmark.get("tags") else []
        tags_str = ", ".join(tags) if tags and tags[0] else "None"
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

        success = delete_bookmark(url=url)

        if success:
            typer.secho("✅ Bookmark deleted successfully!", fg="green")
        else:
            typer.secho("❌ Failed to delete bookmark.", fg="red")

    except Exception as e:
        typer.secho(f"Error deleting bookmark: {e}", fg="red", err=True)
        raise typer.Exit(code=1) from e


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

    This command removes a specified tag from all your bookmarks. By default,
    it will ask for confirmation before deleting. Use the --force option to skip
    the confirmation prompt.

    Args:
        tag: The tag name to delete
        force: Whether to skip the confirmation prompt (default: False)

    Returns:
        None: Results are printed directly to stdout
    """
    if not check_env_variables():
        return

    try:
        if not force:
            confirmed = typer.confirm(
                f"Are you sure you want to delete the tag '{tag}' from all bookmarks?"
            )
            if not confirmed:
                typer.echo("Operation cancelled.")
                return

        success = delete_tag(tag=tag)

        if success:
            typer.secho(f"✅ Tag '{tag}' deleted successfully!", fg="green")
        else:
            typer.secho(f"❌ Failed to delete tag '{tag}'. It might not exist.", fg="red")

    except Exception as e:
        typer.secho(f"Error deleting tag: {e}", fg="red", err=True)
        raise typer.Exit(code=1) from e


# Add top-level commands for reading list and toggle-read
@app.command("reading-list")
def show_reading_list(
    count: int = typer.Option(5, "--count", "-c", help="Number of bookmarks to show"),
):
    """Display your reading list.

    Shows a list of bookmarks with tag #unread.
    This command makes it easy to view your reading queue at a glance.

    Examples:
        linkhut reading-list
        linkhut reading-list --count 10

    Args:
        count: Number of bookmarks to show (default: 5)
    """
    if not check_env_variables():
        return

    try:
        reading_list: list[dict[str, str]] = get_reading_list(count=count)

        if reading_list[0].get("error") == "no_bookmarks_found":
            typer.echo("Your reading list is empty.")
            return
        elif reading_list[0].get("error") == "api_error":
            typer.secho("Error fetching reading list. Something went wrong with the API.", fg="red")
            return

        for i, bookmark in enumerate(reading_list, 1):
            title: str = bookmark.get("description", "No title available")
            url: str = bookmark.get("href", "")
            tags: list[str] = bookmark.get("tags", "").split(" ")
            note: str = bookmark.get("extended", "")

            typer.secho(f"{i}. {title}", fg="bright_white", bold=True)
            typer.echo(f"   URL: {url}")

            if tags:  # Check if tags exist and aren't empty
                tag_str: str = ", ".join(tags)
                typer.echo(f"   Tags: {tag_str}")

            if note:
                typer.echo(f"   Note: {note}")

            typer.echo("")  # Empty line between bookmarks
        typer.echo("\nTo mark as read: linkhut toggle-read URL --not-to-read")
        typer.echo("To view details: linkhut bookmarks list --url URL")

    except Exception as e:
        typer.secho(f"Error fetching reading list: {e}", fg="red", err=True)
        raise typer.Exit(code=1) from e


@app.command("toggle-read")
def toggle_read_status(
    url: str = typer.Argument(..., help="URL of the bookmark"),
    to_read: bool = typer.Option(
        True, "--to-read/--not-to-read", help="Whether to mark as to-read or not"
    ),
    note: str | None = typer.Option(None, "--note", "-n", help="Note to add"),
    tags: list[str] | None = typer.Option(
        None, "--tag", "-g", help="Tags to add if bookmark doesn't exist"
    ),
):
    """Add to reading list or mark as read.

    Quickly add URLs to your reading list or mark them as read.
    Creates a new bookmark if it doesn't exist, or updates an existing one.

    Examples:
        linkhut toggle-read https://example.com              # Add to reading list
        linkhut toggle-read https://example.com --note "Important article"
        linkhut toggle-read https://example.com --tag python --tag cli
        linkhut toggle-read https://example.com --not-to-read # Mark as read
    """
    if not check_env_variables():
        return

    try:
        # First check if the bookmark exists to provide better feedback
        _, status_code = get_bookmarks(url=url)
        bookmark_exists = status_code == 200

        # Call the toggle function
        success = reading_list_toggle(url=url, to_read=to_read, note=note, tags=tags)

        if success:
            action = "Added to" if to_read else "Removed from"

            if bookmark_exists:
                action = "Updated in" if to_read else "Removed from"

            typer.secho(f"✅ {action} reading list!", fg="green")
            typer.echo(f"URL: {url}")

            if tags:
                typer.echo(f"Tags: {', '.join(tags)}")
            if note:
                typer.echo(f"Note: {note}")

            # Show a helpful tip for the next possible action
            if to_read:
                typer.echo("\nTip: View your reading list with 'linkhut reading-list'")
            else:
                typer.echo(
                    f"\nTip: Add it back to your reading list with 'linkhut toggle-read {url}'"
                )
        else:
            typer.secho("❌ Failed to update reading list status.", fg="red")

    except Exception as e:
        typer.secho(f"Error updating reading list: {e}", fg="red", err=True)
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
