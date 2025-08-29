#!/usr/bin/env python3
import os
import argparse
import sys
from page_generator import PageGenerator

def main():
    """
    Main entry point for the website generator
    """
    # Get project root directory
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Generate static website from Canvas database')
    parser.add_argument('--db', type=str, default=os.path.join(project_root, 'canvas.db'),
                        help='Path to SQLite database (default: project_root/canvas.db)')
    parser.add_argument('--templates', type=str, default=os.path.join(project_root, 'frontend/templates'),
                        help='Path to templates directory (default: project_root/frontend/templates)')
    parser.add_argument('--output', type=str, default=os.path.join(project_root, 'frontend/website'),
                        help='Path to output directory (default: project_root/frontend/website)')
    parser.add_argument('--base-url', type=str, default='',
                        help='Base URL path for the site (e.g., "/canvas" for example.com/canvas/)')
    
    args = parser.parse_args()
    
    # Validate paths
    if not os.path.exists(args.db):
        print(f"Error: Database file not found: {args.db}")
        sys.exit(1)
    
    if not os.path.exists(args.templates):
        print(f"Error: Templates directory not found: {args.templates}")
        sys.exit(1)
    
    # Create page generator
    generator = PageGenerator(
        db_path=args.db,
        template_dir=args.templates,
        output_dir=args.output,
        base_url=args.base_url
    )
    
    # Generate all pages
    print(f"Generating website from database: {args.db}")
    print(f"Using templates from: {args.templates}")
    print(f"Output directory: {args.output}")
    if args.base_url:
        print(f"Base URL: {args.base_url}")
    else:
        print("Base URL: (root)")
    
    try:
        generator.generate_all_pages()
        print("Website generation complete!")
    except Exception as e:
        print(f"Error generating website: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 