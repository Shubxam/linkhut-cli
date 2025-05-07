#!/usr/bin/env python3
"""
LinkHut CLI - Command-line interface for managing bookmarks with LinkHut.

This module implements the CLI commands and argument parsing for the LinkHut CLI
application, using the Typer library. It provides commands for managing bookmarks
and tags, checking configuration status, and handling user input.
"""

import typer
import sys
import os
import dotenv

# Add the parent directory to sys.path to be able to import from linkhut_lib
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from linkhut_lib.linkhut_lib import (
    get_bookmarks,
    create_bookmark,
    update_bookmark,
    delete_bookmark,
    get_reading_list,
    rename_tag,
    delete_tag,
    reading_list_toggle
)

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
    missing = []
    if not os.getenv("LH_PAT"):
        missing.append("LH_PAT")
    if not os.getenv("LINK_PREVIEW_API_KEY"):
        missing.append("LINK_PREVIEW_API_KEY")
    
    if missing:
        typer.secho(f"Error: Missing required environment variables: {', '.join(missing)}", fg="red")
        typer.secho(f"Please add them to your .env file or set them in your environment", fg="red")
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
        masked = lp_api_key[:4] + "*" * (len(lp_api_key) - 8) + lp_api_key[-4:] if len(lp_api_key) > 8 else "****"
        typer.echo(f"   API Key: {masked}")
    else:
        typer.secho("❌ Link Preview API Key is not configured", fg="red")

# Bookmark commands
@bookmarks_app.command("list")
def list_bookmarks(
    tag: list[str] | None = typer.Option(None, "--tag", "-t", help="Filter by tags, will only take 1 tag is count is set"),
    count: int|None = typer.Option(None, "--count", "-c", help="Number of bookmarks to show"),
    date: str|None = typer.Option(None, "--date", "-d", help="Date to filter bookmarks(in YYYY-MM-DD format)"),
    url: str|None = typer.Option(None, "--url", "-u", help="URL to filter bookmarks"),
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
            params['count'] = count
            if tag:
                params['tag'] = [tag[0]]
        
        elif tag or date or url:
            params['tag'] = tag
            params['date'] = date
            params['url'] = url

        else:
            params['count'] = 15

        result, status_code = get_bookmarks(**params)
        
        if status_code != 200 or not result or not result.get('posts'):
            typer.echo("No bookmarks found.")
            return
        
        posts = result.get('posts', [])
        typer.echo(f"Found {len(posts)} bookmarks:")
        
        for i, bookmark in enumerate(posts, 1):
            title = bookmark.get('description', 'No title')
            url = bookmark.get('href', '')
            tags = bookmark.get('tags', '').split(',') if bookmark.get('tags') else []
            is_private = bookmark.get('shared') == 'no'
            to_read = bookmark.get('toread') == 'yes'
            
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
        raise typer.Exit(code=1)

@bookmarks_app.command("add")
def add_bookmark(
    url: str = typer.Argument(..., help="URL of the bookmark"),
    title: str|None = typer.Option(None, "--title", "-t", help="Title of the bookmark"),
    note: str|None = typer.Option(None, "--note", "-n", help="Note for the bookmark"),
    tags: list[str]|None = typer.Option(None, "--tag", "-g", help="Tags to associate with the bookmark"),
    private: bool = typer.Option(False, "--private", "-p", help="Make the bookmark private"),
    to_read: bool = typer.Option(False, "--to-read", "-r", help="Mark as to-read"),
):
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
    
    try:
        status_code = create_bookmark(
            url=url, 
            title=title, 
            note=note, 
            tags=tags, 
            private=private, 
            to_read=to_read
        )
        
        if status_code == 200:
            typer.secho("✅ Bookmark created successfully!", fg="green")
            typer.echo(f"URL: {url}")
            if title:
                typer.echo(f"Title: {title}")
            if tags:
                typer.echo(f"Tags: {', '.join(tags)}")
            if private:
                typer.echo("Visibility: Private")
            if to_read:
                typer.echo("Marked as: To Read")
        else:
            typer.secho(f"❌ Error creating bookmark. Status code: {status_code}", fg="red")
            
    except Exception as e:
        typer.secho(f"Error creating bookmark: {e}", fg="red", err=True)
        raise typer.Exit(code=1)


@bookmarks_app.command("update")
def update_bookmark_cmd(
    url: str = typer.Argument(..., help="URL of the bookmark to update"),
    tags: list[str]|None = typer.Option(None, "--tag", "-g", help="New tags for the bookmark"),
    note: str|None = typer.Option(None, "--note", "-n", help="Note to append to the bookmark"),
    private: bool|None = typer.Option(None, "--private/--public", help="Update bookmark privacy"),
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
        success = update_bookmark(
            url=url,
            new_tag=tags,
            new_note=note,
            private=private
        )
        
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
        raise typer.Exit(code=1)


@bookmarks_app.command("delete")
def delete_bookmark_cmd(
    url: str = typer.Argument(..., help="URL of the bookmark to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Delete without confirmation"),
):
    """Delete a bookmark from your LinkHut account.
    
    This command deletes a bookmark identified by its URL. By default, it will
    ask for confirmation before deleting. Use the --force option to skip the
    confirmation prompt.
    
    Returns:
        None: Results are printed directly to stdout
    """
    if not check_env_variables():
        return
    
    try:
        if not force:
            confirmed = typer.confirm(f"Are you sure you want to delete bookmark with URL: {url}?")
            if not confirmed:
                typer.echo("Operation cancelled.")
                return
        
        success = delete_bookmark(url=url)
        
        if success:
            typer.secho("✅ Bookmark deleted successfully!", fg="green")
        else:
            typer.secho("❌ Failed to delete bookmark. It might not exist.", fg="red")
            
    except Exception as e:
        typer.secho(f"Error deleting bookmark: {e}", fg="red", err=True)
        raise typer.Exit(code=1)


@bookmarks_app.command("reading-list")
def show_reading_list(
    count: int = typer.Option(5, "--count", "-c", help="Number of bookmarks to show")
):
    """Show your reading list (bookmarks marked as to-read).
    
    This command fetches and displays your reading list, which consists of
    bookmarks you've marked as 'to-read'. You can specify how many items
    to display.
    
    Args:
        count: Number of bookmarks to show (default: 5)
        
    Returns:
        None: Results are printed directly to stdout
    """
    if not check_env_variables():
        return
    
    try:
        get_reading_list(count=count)
        # Output formatting is handled by the get_reading_list function
    except Exception as e:
        typer.secho(f"Error fetching reading list: {e}", fg="red", err=True)
        raise typer.Exit(code=1)


@bookmarks_app.command("toggle-read")
def toggle_read_status(
    url: str = typer.Argument(..., help="URL of the bookmark"),
    to_read: bool = typer.Option(True, "--to-read/--not-to-read", help="Whether to mark as to-read or not"),
    note: str|None = typer.Option(None, "--note", "-n", help="Note to add"),
    tags: list[str]|None = typer.Option(None, "--tag", "-g", help="Tags to add if bookmark doesn't exist"),
):
    """Toggle the to-read status of a bookmark.
    
    This command marks a bookmark as either 'to-read' or 'read'. If the bookmark
    doesn't exist yet, it will be created with the specified status. You can also
    add a note to the bookmark and specify tags if it's being created.
    
    By default, bookmarks are marked as to-read. Use --not-to-read to mark as read.
    
    Returns:
        None: Results are printed directly to stdout
    """
    if not check_env_variables():
        return
    
    try:
        success = reading_list_toggle(url=url, to_read=to_read, note=note, tags=tags)
        
        if success:
            status = "to-read" if to_read else "read"
            typer.secho(f"✅ Bookmark marked as {status}!", fg="green")
        else:
            typer.secho("❌ Failed to update bookmark read status.", fg="red")
            
    except Exception as e:
        typer.secho(f"Error updating read status: {e}", fg="red", err=True)
        raise typer.Exit(code=1)


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
        raise typer.Exit(code=1)


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
            confirmed = typer.confirm(f"Are you sure you want to delete the tag '{tag}' from all bookmarks?")
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
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()