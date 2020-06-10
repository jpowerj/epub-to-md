[Right now this doesn't convert all the way to .md, it just takes the raw .html files inside the .epub, combines them, and outputs a single .html file (that could technically be converted to .md directly but I need to do more work to get the footnotes/internal links working)]

Usage: just put the .epub file in the same directory as epub_to_html.py, and run it like

`python epub_to_html.py <filename>.epub`

If there are no errors it will output a `<filename>.html` file with the raw html contents of the book.

Work in progress.