# LinkHut CLI

[![PyPI Downloads](https://static.pepy.tech/badge/linkhut-cli)](https://pepy.tech/projects/linkhut-cli)

A powerful command-line interface for managing your bookmarks with LinkHut. Efficiently add, update, delete, and organize your bookmarks directly from the terminal.

![alt text](res/image.png)

## Features

- **Bookmark Management**: Add, update, delete, and list bookmarks
- **Tag Management**: Rename and delete tags across all bookmarks
- **Reading List**: Maintain a reading list with to-read/read status toggling
- **Features**: 
  - Automatic title fetching when adding bookmarks
  - Tag suggestions based on bookmark content
  - Rich formatting for improved readability

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

## Usage Guide

### Managing Bookmarks

#### Listing Bookmarks

![alt text](res/image-1.png)

```bash
# List your most recent bookmarks (default: 15)
linkhut bookmarks list

# List with tag filtering
linkhut bookmarks list --tag python --tag cli

# Limit the number of results
linkhut bookmarks list --count 20

# Filter by specific date (YYYY-MM-DD format)
linkhut bookmarks list --date 2023-01-01

# Search for a specific URL
linkhut bookmarks list --url https://example.com
```

#### Adding Bookmarks

![alt text](res/image-2.png)

```bash
# Add with minimal info (title will be fetched automatically)
linkhut bookmarks add https://example.com

# Add with full details
linkhut bookmarks add https://example.com \
  --title "Example Site" \
  --note "This is a note about the site" \
  --tag 'dev python' \
  --private \
  --to-read
```

#### Updating Bookmarks

![alt text](res/image-3.png)

```bash
# Update tags
linkhut bookmarks update https://example.com --tag newtag1 --tag newtag2

# Append a note
linkhut bookmarks update https://example.com --note "Additional notes"

# Change privacy setting
linkhut bookmarks update https://example.com --private  # or --public
```

#### Deleting Bookmarks

![alt text](res/image-4.png)

```bash
# Delete with confirmation prompt
linkhut bookmarks delete https://example.com

# Delete without confirmation
linkhut bookmarks delete https://example.com --force
```

### Reading List Operations

#### Show Reading List

![alt text](res/image-5.png)

```bash
# View your reading list in tabular format
linkhut reading-list

# Customize number of items shown
linkhut reading-list --count 10
```

#### Toggle Read Status

![alt text](res/image-6.png)

```bash

# Add to reading list (mark as to-read)
linkhut toggle-read https://example.com

# Add with note and tags
linkhut toggle-read https://example.com --note "Read by Friday" --tag python --tag article

# Mark a bookmark as read
linkhut toggle-read https://example.com --not-to-read
```

### Managing Tags

![alt text](res/image-7.png)

```bash
# Rename a tag across all bookmarks
linkhut tags rename old-tag-name new-tag-name

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
