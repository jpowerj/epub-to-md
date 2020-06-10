# Python imports
import six
import sys
import zipfile

# 3rd party imports
from lxml import html, etree

# This first helper function adapted from ebooklib code
def get_body_content(html_str):
    utf8_parser = html.HTMLParser(encoding='utf-8')
    html_tree = html.document_fromstring(html_str, parser=utf8_parser)
    html_root = html_tree.getroottree()
    if len(html_root.find('body')) != 0:
        body = html_tree.find('body')
        tree_str = etree.tostring(body, pretty_print=True, encoding='utf-8', xml_declaration=False)
        # this is so stupid
        if tree_str.startswith(six.b('<body>')):
            n = tree_str.rindex(six.b('</body>'))
            return tree_str[6:n]
        return tree_str
    return ''

def epub_to_html(epub_fpath):
    epub_zip = zipfile.ZipFile(epub_fpath)
    section_contents = []
    html_fpaths = sorted([name for name in epub_zip.namelist() if name.endswith(".html")])
    for cur_fpath in html_fpaths:
        with epub_zip.open(cur_fpath) as f:
            html_contents = f.read()
        parsed_body_str = get_body_content(html_contents).decode('utf-8')
        section_contents.append(parsed_body_str)
    all_html = "".join(section_contents)
    output_fpath = epub_fpath.replace(".epub",".html")
    with open(output_fpath, "w", encoding='utf-8') as g:
        g.write(all_html)
    return output_fpath

def main():
    if len(sys.argv) < 2:
        print("Error: requires a single command-line argument with the path to the .epub file")
        return
    epub_fpath = sys.argv[1]
    output_fpath = epub_to_html(epub_fpath)
    print(f"Extracted .html saved to {output_fpath}")

if __name__ == "__main__":
    main()