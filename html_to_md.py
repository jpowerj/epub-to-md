import os
import re
import bs4

debug = False
dprint = print if debug else lambda *args: None

fn_template = '<sup id="t{fn_num}">[{fn_num}](#f{fn_num})</sup>'
# Version with numbers, commented out since the numbers are "built into" the footnotes in Killing Hope,
# i.e. the span contains the numbers along with the actual text
#rfn_template = '{fn_num}. <span id="f{fn_num}" name="f{fn_num}">{fn_text}</span> [↩](#t{fn_num})'
rfn_template = '<span id="f{fn_num}" name="f{fn_num}">{fn_text}</span> [↩](#t{fn_num})'

repl_dict = {
    '’': "'",
    '‘': "'",
    '“': '"',
    '”': '"',
    '—': '--',
    '…': '...'
}

# Detects "human-readable" chapter num, like "3. Blah Blah"
ch_reg = re.compile(r'([0-9]+)\. (.+)$')
# Detects Calibre chapter ids, like "ch8", "ch9", "ch10", and so on
chid_reg = re.compile(r'ch([0-9]{1,2})')
alphabet = "abcdefghijklmnopqrstuvwxyz"

def parse_toc(soup):
    nonum_counter = 0
    toc_elts = soup.find_all(class_="toc")
    ch_info = []
    for elt_num, cur_elt in enumerate(toc_elts):
        #print(cur_elt)
        # Here we can get the id for the link
        elt_id = cur_elt['id']
        #print(elt_num, elt_id)
        # But the main thing is getting the href and the text of the link
        children = cur_elt.children
        # I think there should only be one child, so this should work
        child = next(children)
        # Grr. Nope, because sometimes the first child can be an anchor marking a new page
        if 'href' not in child.attrs:
            child = next(children)
        #print(child)
        #print(dir(elt_child))
        #print(elt_child.attrs)
        href = child.attrs['href']
        href_elts = href.split("#")
        html_file = href_elts[0]
        anchor_link = href_elts[1]
        # Important: here we also record this anchor_link as "next_anchor" for the previous
        # chapter's info
        if elt_num > 0:
            ch_info[elt_num-1]['next_anchor'] = anchor_link
        text = child.text
        # Replace annoying unicode chars in the text b/c I'm neurotic
        repl_unicode = lambda x: repl_dict[x] if x in repl_dict else x
        text = "".join([repl_unicode(c) for c in text])
        # And now get the chapter num if it has one
        ch_title = text
        ch_reg_result = ch_reg.search(text)
        if ch_reg_result is not None:
            # We have a ch_num
            ch_num = ch_reg_result.group(1)
            # And also update the title so it doesn't contain the ch num redundantly
            ch_title = ch_reg_result.group(2)
        else:
            # 00a, 00b, ... the % is just so it doesn't crash if more than 26 (it just starts repeating)
            ch_num = "00" + alphabet[nonum_counter % len(alphabet)]
            nonum_counter = nonum_counter + 1
        #print(ch_num, href, text)
        ch_info.append({'ch_num':ch_num, 'ch_title': ch_title, 'href':href, 'html_file':html_file, 'anchor_link':anchor_link})
    return ch_info

def extract_chapter(ch_info, soup):
    ch_anchor = ch_info['anchor_link']
    next_anchor = ch_info['next_anchor'] if 'next_anchor' in ch_info else None
    ch_start_elt = soup.find(id=ch_anchor)
    ch_contents = []
    for cur_ch_elt in ch_start_elt.next_siblings:
        try:
            cur_id = cur_ch_elt.attrs['id']
            if cur_id == next_anchor:
                break
            ch_contents.append(cur_ch_elt)
        except AttributeError as ae:
            # It's a NavigableString. Often an annoying linebreak that we don't need, but
            # if not then we don't throw it away (we append it to ch_contents)
            if repr(cur_ch_elt) != '\n':
                ch_contents.append(cur_ch_elt)
            #print(ae)
        except KeyError as ke:
            # It's an element without an id, which we always want to keep
            ch_contents.append(cur_ch_elt)
            #print(ke)
    # Don't ask me how but sometimes "\n" lines still find their way into ch_contents...
    ch_contents = [c for c in ch_contents if c != '\n']
    return ch_contents
    
def parse_footnote(fn_elt):
    """
    Specifically parse the BeautifulSoup element containing the reference (i.e., link and anchor
    stuff inside the seemingly-simple <sup>1</sup>)
    """
    #print(fn_elt)
    fn_children = fn_elt.children
    # First child should be the return anchor
    return_anchor = next(fn_children)
    return_id = return_anchor.attrs['id']
    dprint(f"return_id = {return_id}")
    # And next should be the link to the footnote itself
    fn_link = next(fn_children)
    fn_href = fn_link.attrs['href']
    dprint(f"fn_href = {fn_href}")
    fn_text = fn_link.text
    # But really fn_text should be a number
    fn_num = int(fn_text)
    dprint(f"fn_num = {fn_num}")
    # Cool so now we should be able to convert it to our md format
    new_fn_html = fn_template.format(fn_num=fn_num)
    return new_fn_html, fn_href, return_id

def parse_paragraph(p_elt):
    #print("---")
    #print("parse_paragraph()")
    #print(p_elt)
    pconv_buffer = ""
    fn_info = []
    # See if it's a header
    p_class = " ".join(p_elt.attrs['class'])
    if "title" in p_class:
        # Make it markdown header text
        pconv_buffer += "## "
        # And see if we can extract the chapter num as well
        ch_num_result = chid_reg.search(str(p_elt))
        if ch_num_result is not None:
            ch_num = ch_num_result.group(1)
            pconv_buffer += f"{ch_num}. "
    # Now... I'm gonna try to loop over children
    for se_num, sub_elt in enumerate(p_elt.children):
        #print(f"sub_elt #{se_num} ({type(sub_elt)}): {sub_elt}")
        # Seems like they're either Tags or NavigableStrings
        if type(sub_elt) == bs4.element.Tag:
            #print(f"**tag**: {sub_elt}")
            if sub_elt.name == "a":
                # A link! Just extract the text
                pconv_buffer += sub_elt.text
            elif sub_elt.name == "sup":
                # A footnote!
                fn_html, fn_href, return_id = parse_footnote(sub_elt)
                pconv_buffer += fn_html
                fn_info.append((fn_html, fn_href, return_id))
            elif sub_elt.name == "i":
                # Just italics
                pconv_buffer += f"*{sub_elt.text}*"
            elif sub_elt.name == "b":
                # Bold
                pconv_buffer += f"**{sub_elt.text}**"
            elif sub_elt.name == "span":
                # This seems to be how it does blockquotes
                #print("\n\nspan?!?\n\n")
                #print(sub_elt)
                pconv_buffer += f"> "
            elif sub_elt.name == "br":
                # Random linebreaks, dunno why, skipping
                pass
            elif sub_elt.name == "img":
                # We don't handle images for now, though it wouldn't be difficult to do
                pass
            else:
                raise Exception(f"Unhandled tag: {sub_elt}")
        elif type(sub_elt) == bs4.element.NavigableString:
            #print(f"**NS**: {sub_elt}")
            pconv_buffer += str(sub_elt)
        else:
            raise Exception("smth bad happened")
    # The final step: removing all the annoying unicode chars
    remove_uc = lambda x: repl_dict[x] if x in repl_dict else x
    pconv_buffer = "".join([remove_uc(c) for c in pconv_buffer])
    #print("---")
    return pconv_buffer, fn_info

def parse_chapter(ch_elts):
    parsed_elts = []
    for elt_num, cur_ch_elt in enumerate(ch_elts):
        #print(f"=====[Parsing chapter element #{elt_num}]=====")
        cur_tag = cur_ch_elt.name
        if cur_tag == "p":
            # Cool, it's a paragraph. Parse it.
            parsed = parse_paragraph(cur_ch_elt)
            #print(parsed)
            parsed_elts.append(parsed)
            #print(f"=====[end #{elt_num}]=====")
    return parsed_elts

def extract_footnote(soup, fn_anchor, next_anchor):
    """
    Can pass in next_anchor=None in which case we revert to the sketchier heuristic of just
    scanning until we find another tag with an id
    """
    full_fn = []
    fn_pointer = soup.find(id=fn_anchor)
    while fn_pointer is not None:
        # If it's a Tag we need to use .text, otherwise it's a NavigableString and we can just convert it to str
        elt_text = fn_pointer.text if type(fn_pointer) == bs4.element.Tag else str(fn_pointer)
        full_fn.append(elt_text)
        fn_pointer = fn_pointer.next_sibling
        # If next_anchor is None, we don't care about what the id is
        if next_anchor is None:
            at_next_fn = (type(fn_pointer) == bs4.element.Tag) and (('id' in fn_pointer.attrs) or (fn_pointer.name == "p"))
        else:
            # We want the id to specifically be next_anchor
            at_next_fn = (type(fn_pointer) == bs4.element.Tag) and ('id' in fn_pointer.attrs) and (fn_pointer.attrs['id'] == next_anchor)
        if at_next_fn:
            break
    # This is slightly better than a basic .replace() since it "collapses" all repeated
    # non-breaking spaces down to a single space
    nbspace_reg = re.compile(r'(\xa0)+')
    #"".join([fn_line.replace("\xa0"," ") for fn_line in full_fn7])
    fn_str = "".join([nbspace_reg.sub(" ", fn_line) for fn_line in full_fn])
    fn_str = fn_str.strip()
    return fn_str

def extract_footnotes(soup, parsed_elts):
    # First let's get all the footnote tuples for the ch into one big list
    all_fn_info = []
    for cur_elt in parsed_elts:
        footnote_list = cur_elt[1]
        if len(footnote_list) > 0:
            all_fn_info.extend(footnote_list)
    # If all_fn_info is still empty, either there's an error or
    # the chapter just doesn't have any footnotes (like the front matter)
    # But we return None (instead of the empty string which would be
    # returned after all the stuff below runs) to indicate this
    if len(all_fn_info) == 0:
        return None
    # Just get the id of the anchor that the footnote links to
    fn_anchors = [fn_info[1].split("#")[1] for fn_info in all_fn_info]
    # Now we just find those anchors (#rfn1ch9, #rfn2ch9, ...) and extract their contents
    all_fn_contents = []
    for i in range(len(fn_anchors)):
        cur_anchor = fn_anchors[i]
        next_anchor = fn_anchors[i+1] if i+1 < len(fn_anchors) else None
        fn_contents = extract_footnote(soup, cur_anchor, next_anchor)
        all_fn_contents.append((cur_anchor, fn_contents))
    #results = [(fn_anchor, extract_footnote(fn_anchor)) for fn_anchor in fn_anchors]
    # Now that we've got the contents we can use rfn_template to format them as the MD we want
    fn_html_strs = []
    for iter_num, cur_fn_contents in enumerate(all_fn_contents):
        # Footnotes start counting from 1, not 0
        fn_num = iter_num + 1
        fn_text = cur_fn_contents[1]
        fn_html = rfn_template.format(fn_num=fn_num, fn_text=fn_text)
        fn_html_strs.append(fn_html)
    # Two linebreaks b/c Markdown doesn't make new paragraphs for single linebreaks
    all_fns_str = "\n\n".join(fn_html_strs)
    
def save_chapter_md(ch_text, md_fname, book_name):
    # Annoying that this is a whole separate function but yeah we gotta make the
    # "chapters" folder if it doesn't exist yet and stuff
    #print(f"save_chapter_md({md_fname})")
    if not os.path.isdir(book_name):
        os.mkdir(book_name)
    output_fpath = os.path.join(book_name, md_fname)
    with open(output_fpath, "w", encoding="utf-8") as f:
        f.write(ch_text)

def main():
    """
    TODO: The last step would be taking the TOC and updating all the links so they point to the
    generated .md files rather than files/anchors in the original html...
    """
    html_fname = "killing_hope.html"
    # (book_name is for later when we save the individual chapters into a folder)
    book_name = html_fname.replace(".html","")
    with open(html_fname, "r", encoding="utf-8") as f:
        html_str = f.read()
    soup = bs4.BeautifulSoup(html_str, 'html.parser')
    # Get a list with the basic info on each chapter (most importantly its location) by parsing TOC
    ch_info = parse_toc(soup)
    # Loop over chapters, parsing as we go
    for cur_ch_info in ch_info:
        #print(cur_ch_info)
        ch_num = cur_ch_info['ch_num']
        full_title = cur_ch_info['ch_title']
        # Annoyingly, we need to split on ":" so we don't include the long subtitles for each chapter
        if ":" in full_title:
            ch_title = full_title.split(":")[0]
            #print(f"Reduced '{full_title}' to '{ch_title}'")
        else:
            ch_title = full_title
        print(f"Processing #{ch_num}, {ch_title}")
        ### Part 1: The actual chapter contents
        # Extract and just the specific chapter's html, out of the full soup
        ch_elts = extract_chapter(cur_ch_info, soup)
        # And now we gotta parse each element, specifically keeping track of all footnote info
        parsed_elts = parse_chapter(ch_elts)
        # Now we just join each paragraph with two linebreaks (b/c Markdown doesn't
        # make paragraph breaks for text separated by a single linebreak)
        ch_lines = [pe[0] for pe in parsed_elts]
        ch_contents = "\n\n".join(ch_lines)
        ### Part 2: Going and getting the text of all the footnotes (note that we go "back"
        ### to parsed_elts instead of ch_lines or ch_contents, because the latter two throw
        ### away the info we need for this part)
        all_fns_str = extract_footnotes(soup, parsed_elts)
        ### Part 3: Combine original chapter contents with extracted footnotes to make a
        ### single file for the whole chapter
        # Start with just the main text of the chapter
        ch_full = ch_contents
        # And if we have at least one footnote, add a footnotes section and drop them in
        if all_fns_str is not None:
            ch_full = ch_full + "\n\n# Footnotes\n\n" + all_fns_str
        if ch_num is not None:
            # Format the chapter num so it has trailing zeros ("01", "02", ...)
            ch_num_str = str(ch_num).zfill(2)
        else:
            ch_num_str = str(0).zfill(2)
        cleaned_title = ch_title.replace(" ","_").replace("'","").replace("/","_")
        ch_fname = f"{ch_num_str}_{cleaned_title}.md"
        save_chapter_md(ch_full, ch_fname, book_name)

if __name__ == "__main__":
    main()