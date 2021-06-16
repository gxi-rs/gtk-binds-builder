import asyncio
import os
import shutil

import requests
from bs4 import BeautifulSoup

BASE_OUTPUT_DIR = 'binds/desktop'
WIDGETS_OUTPUT_DIR = f'{BASE_OUTPUT_DIR}/widgets'
CONTAINERS_OUTPUT_DIR = f'{BASE_OUTPUT_DIR}/containers'
TOP_LEVEL_WIDGETS_OUTPUT_DIR = f'{BASE_OUTPUT_DIR}/top_level_widgets'

RUST_KEYWORDS = ['box']

TOP_LEVEL_WIDGET_LIST = [
    'Window'
]

BASE_URL = 'https://docs.rs/gtk/0.9.2/gtk'


def to_rust_valid(value):
    res = [value[0].lower()]
    for c in value[1:]:
        if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            res.append('_')
            res.append(c.lower())
        else:
            res.append(c)
    result = ''.join(res)
    if RUST_KEYWORDS.__contains__(result):
        result += "_"
    return result


async def do(tr, container_mod_file, widgets_mod_file):
    a = tr.select_one("a")
    gtk_node = a['title'].split(' ')[0].split('::')[1]
    if not gtk_node.endswith('Class') and not gtk_node.endswith('Group') and not gtk_node.endswith(
            'Builder'):
        gtk_node_url = f"{BASE_URL}/{a['href']}"
        req = await asyncio.get_event_loop().run_in_executor(None, requests.get, gtk_node_url)
        is_a_container = req.text.__contains__('impl-IsA%3CContainer%3E')
        is_a_widget = is_a_container
        if not is_a_container:
            is_a_widget = req.text.__contains__('impl-IsA%3CWidget%3E')
        gtk_node_file_name = to_rust_valid(gtk_node)
        mod = f"pub mod {gtk_node_file_name};\npub use {gtk_node_file_name}::*;\n"

        if is_a_widget:
            print(f"{BASE_URL}/{a['href']}")
            print(f"{gtk_node} is_a_container: {is_a_container} is_a_widget: {is_a_widget}")

            doc_comment = f"//! [{gtk_node}]({gtk_node_url})"

            if is_a_container:
                output_file = open(f"{CONTAINERS_OUTPUT_DIR}/{gtk_node_file_name}.rs", 'w')
                output_file.write(f"""{doc_comment}
use crate::*;
create_widget!({gtk_node});
impl_widget!({gtk_node});""")
                container_mod_file.write(mod)
            else:
                output_file = open(f"{WIDGETS_OUTPUT_DIR}/{gtk_node_file_name}.rs", 'w')
                output_file.write(f"""{doc_comment}
use crate::*;
create_widget!({gtk_node});
impl_widget!({gtk_node});""")
                widgets_mod_file.write(mod)


async def main():
    for path in [BASE_OUTPUT_DIR, CONTAINERS_OUTPUT_DIR, WIDGETS_OUTPUT_DIR]:
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.mkdir(path)

    req = requests.get(BASE_URL)
    html = BeautifulSoup(req.text, 'html.parser')
    prev_h2 = html.select_one("#structs")
    table = prev_h2.find_next_sibling('table')
    container_mod_file = open(f'{CONTAINERS_OUTPUT_DIR}/mod.rs', 'w')
    widgets_mod_file = open(f'{WIDGETS_OUTPUT_DIR}/mod.rs', 'w')
    tasks = [do(tr, container_mod_file, widgets_mod_file) for tr in table.children]
    await asyncio.wait(tasks)


asyncio.run(main())
