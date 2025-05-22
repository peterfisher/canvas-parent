# Canvas Scorecard Frontend Generator

This directory contains code for generating static HTML/JS pages from the Canvas database.

## Directory Structure

- `generate_site.py`: Main script to generate the static website
- `page_generator.py`: Class that handles template rendering and HTML generation
- `templates/`: Directory containing HTML templates and static files
  - `base.html`: Base template that all other templates extend
  - `index.html`: Template for the main index page
  - `student.html`: Template for individual student pages
  - `static/`: Static files (CSS, JavaScript, images)
    - `css/`: CSS stylesheets
    - `js/`: JavaScript files
- `website/`: Output directory for generated static HTML/JS pages

## Usage

To generate the static website, run:

```bash
python frontend/generate_site.py
```

By default, this will:
1. Read data from `canvas.db` in the project root
2. Use templates from `frontend/templates/`
3. Output static files to `frontend/website/`

### Command-line Options

You can customize the paths using command-line options:

```bash
python frontend/generate_site.py --db=path/to/database.db --templates=path/to/templates --output=path/to/output
```

- `--db`: Path to the SQLite database (default: `canvas.db`)
- `--templates`: Path to the templates directory (default: `frontend/templates`)
- `--output`: Path to the output directory (default: `frontend/website`)

## Templates

Templates use the Jinja2 templating engine. All templates extend the base template (`base.html`) and override specific blocks:

- `title`: Page title
- `extra_head`: Additional content for the `<head>` section
- `nav_items`: Additional navigation items
- `content`: Main page content
- `scripts`: Additional JavaScript at the end of the page

## Adding New Templates

To add a new page template:

1. Create a new HTML file in the `templates` directory
2. Extend the base template: `{% extends "base.html" %}`
3. Override the necessary blocks
4. Update the `PageGenerator` class to generate pages using the new template

## Static Files

Static files (CSS, JavaScript, images) are stored in the `templates/static/` directory and automatically copied to the output directory during website generation.

## Deploying to a Web Server

After generating the static site, the contents of the `website/` directory can be copied to a web server (e.g., nginx) for hosting. 