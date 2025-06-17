# LinkHut CLI

[![PyPI Downloads](https://static.pepy.tech/badge/linkhut-cli)](https://pepy.tech/projects/linkhut-cli)
[![PyPI version](https://badge.fury.io/py/linkhut-cli.svg)](https://badge.fury.io/py/linkhut-cli)

A powerful command-line interface for managing your bookmarks with LinkHut. Efficiently add, update, delete, and organize your bookmarks directly from the terminal.

![alt text](res/header.png)

## Features

- **Bookmark Management**: Add, update, delete, and list bookmarks
- **Tag Management**: Rename and delete tags across all bookmarks
- **Reading List**: Maintain a reading list with to-read/read status toggling
- **Features**: 
  - Automatic title fetching when adding bookmarks.
  - Tag suggestions based on bookmark content.
  - Rich formatting for improved readability.
  - Auto completion for commands and options using Tab key.

## Installation

### Option 1: Install from PyPI (recommended)

```bash
pip install linkhut-cli
```

### Option 2: Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/linkhut-cli.git
cd linkhut-cli

# Install in development mode
pip install -e .
```

## Configuration

The CLI requires two environment variables to function:

- `LH_PAT`: Your LinkHut Personal Access Token. (sign in and get it from [here](https://ln.ht/_/oauth))
- `LINK_PREVIEW_API_KEY`: Free API key for fetching link previews (get it for free from [here](https://my.linkpreview.net/access_keys))

You can set these in a `.env` file in the project root or set them in your environment.

### Checking Configuration

```bash
# Verify your configuration status
linkhut config_status
```

### Handy Aliases
You can set up aliases in your shell configuration file (e.g., `.bashrc`, `.zshrc`) for convenience:

```bash
alias bm='linkhut'
alias bg='bm bookmarks get'
alias ba='bm bookmarks add'
alias rl='bm reading-list'
```

all the flags and options stay the same.


## Usage Guide

### Managing Bookmarks
![bookmarks get help menu](res/bookmarks.png)

#### Get Bookmarks

![bookmarks get operation](res/bookmarks-get.png)

```bash
# get your most recent bookmarks (default: 15)
linkhut bookmarks get

# get bookmarks filtered by tags seperated by commas, separated by spaces inside quotes or mix and match
linkhut bookmarks get -g stream,cricket
linkhut bookmarks get -g 'stream cricket'
linkhut bookmarks get -g 'stream, cricket'

# se the count of bookmarks to fetch
linkhut bookmarks get -g stream -c 5

# Filter by specific date (YYYY-MM-DD format)
linkhut bookmarks get -d 2025-05-19 -g personal-blog -c 4

# Search for a specific URL
# because of limitation of the API, it can only match exact URLs
linkhut bookmarks get -u https://registry.jsonresume.org/
```

#### Adding Bookmarks

![alt text](res/bookmarks-add.png)

If the url already exists, program will throw an error. You can add -R flag to replace the existing bookmark.

```bash
# Add a bookmark with just the URL (title and tags will be fetched automatically)
linkhut bookmarks add https://example.com

# Add with full details
linkhut bookmarks add https://github.com/xiangechen/chili3d -g "simulation, 3d, cad, blender" -n "A browser based 3D simulation engine"

# Add multiple bookmarks seperated by commas or newlines inside quotes
ba "https://github.com/thomasdavis/resume
https://www.npmjs.com/package/jsonresume-theme-onepage-plus
https://github.com/vkcelik/jsonresume-theme-onepage-plus
https://www.npmjs.com/package/jsonresume-theme-even"
```

#### Updating Bookmarks

![alt text](res/bookmarks-update.png)

The default behavior of the update command is to append tags and notes to the existing bookmark. If you want to replace the existing tags or notes, you can use the `-R` flag.

```bash
# replace existing tags
linkhut bookmarks update https://audiophile.fm/intense-radio -g "audio,stream,radio" -R

# Append to existing note
linkhut bookmarks update https://audiophile.fm/intense-radio -n "New note content"

# Change privacy setting
linkhut bookmarks update https://macthemes.garden/ -g 'macos, themes' --private
```

#### Deleting Bookmarks

This command deletes a bookmark identified by its URL. It first shows the bookmark
    details and then asks for confirmation before deleting. Use the --force option
    to skip the confirmation prompt.

![alt text](res/bookmarks-delete.png)


```bash
# Delete with confirmation prompt
linkhut bookmarks delete https://www.depthofml.in

# Delete without confirmation
linkhut bookmarks delete https://www.depthofml.in --force
```

### Reading List Operations

Manage Items in your reading list with ease. You can add items to your reading list, mark them as read, or toggle their status.
While toggling, you can also add notes and tags to the items.

![alt text](res/reading-list.png)

```bash
# show 5 most recent reading list items
linkhut reading-list

# show most recent n reading list items
linkhut reading-list --count 10

# Add a bookmark to your reading list
linkhut reading-list https://example.com --to-read

# Mark item as read with tags and notes
linkhut reading-list https://example.com --read -g "python, cli" -n "Good read, shows the power of CLI tools"
```

### Managing Tags

Allows you to rename or delete tags across all bookmarks. This is useful for maintaining consistency in your tagging system.

![alt text](res/tags.png)

#### Renaming Tags

![alt text](res/tags-rename.png)

```bash
# Rename a tag across all bookmarks
linkhut tags rename old-tag-name new-tag-name
```

#### Deleting Tags

![alt text](res/tags-delete.png)

```bash
# Delete a tag from all bookmarks (with confirmation)
linkhut tags delete tag-name

# Delete a tag without confirmation
linkhut tags delete tag-name --force
```

## Help and Documentation

```bash
# Get general help
linkhut --help

# Get help for a specific command group
linkhut bookmarks --help

# Get help for a specific command
linkhut bookmarks add --help
```

## Development

Please refer to the [development guide](development.md) for information on contributing to this project.

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file included in the repository.
