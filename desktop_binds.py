import asyncio
import os
import shutil

import requests
from bs4 import BeautifulSoup

# out dirs
BASE_OUTPUT_DIR = 'binds/desktop'
WIDGETS_OUTPUT_DIR = f'{BASE_OUTPUT_DIR}/widgets'
CONTAINERS_OUTPUT_DIR = f'{BASE_OUTPUT_DIR}/containers'
TOP_LEVEL_WIDGETS_OUTPUT_DIR = f'{BASE_OUTPUT_DIR}/top_level_widgets'

# rust keywords which should not match the generated binding's file name
ALTERNATIVES = {
    'Box': 'View'
}

# list of all top level widgets
TOP_LEVEL_WIDGET_LIST = [
    'Window',
]

BLACKLIST = [
    'ModelButton',
    'ToolButton',
    'PopoverMenu',
    'Container',
    'ShortcutsSection',
    'ShortcutsWindow',
    'ShortcutLabel',
    'ShortcutsShortcut',
    'StackSidebar',
    'GLArea',
]

# gxi-rs docs.rs url
BASE_URL = 'https://docs.rs/gtk/0.9.2/gtk'


# converts string to snake case and if the name is a rust keyword then appends a _ to it
def to_snake_case(value):
    res = [value[0].lower()]
    for c in value[1:]:
        if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            res.append('_')
            res.append(c.lower())
        else:
            res.append(c)
    return ''.join(res)


async def scrap(tr, top_level_mod_file, container_mod_file, widgets_mod_file):
    # get the name of the widget
    a = tr.select_one("a")
    struct = a['title'].split(' ')[0].split('::')[1]

    if BLACKLIST.__contains__(struct):
        return
    # if it ends with Class, Group or Builder then it's not a widget
    if not struct.endswith('Class') and not struct.endswith('Group') and not struct.endswith(
            'Builder'):
        # url to doc of the widget
        gtk_node_url = f"{BASE_URL}/{a['href']}"
        # check if node is a widget or a container or both or none
        req = await asyncio.get_event_loop().run_in_executor(None, requests.get, gtk_node_url)
        # if it implements IsA<container> then it is a container and a widget as well
        is_a_container = req.text.__contains__('impl-IsA%3CContainer%3E')
        is_a_widget = is_a_container
        # if it not a container then check if it is a widget
        if not is_a_container:
            is_a_widget = req.text.__contains__('impl-IsA%3CWidget%3E')

        if is_a_widget:
            # generate valid name for the node
            node_name = struct
            file_name = ''
            # check if there is any alternative
            if ALTERNATIVES.__contains__(struct):
                file_name = to_snake_case(ALTERNATIVES[struct])
                node_name = ALTERNATIVES[struct]
            else:
                file_name = to_snake_case(struct)
            # entry in mod.rs
            mod = f"mod {file_name};\npub use {file_name}::*;\n"

            print(f"{BASE_URL}/{a['href']}")
            print(
                f"{struct} is_a_container: {is_a_container} is_a_widget: {is_a_widget}")
            # doc
            doc_comment = f"//! [{struct}]({gtk_node_url})"
            # write to file accordingly
            if is_a_container:
                if TOP_LEVEL_WIDGET_LIST.__contains__(struct):
                    output_file = open(
                        f"{TOP_LEVEL_WIDGETS_OUTPUT_DIR}/{node_name}.rs", 'w')
                    output_file.write(f"""{doc_comment}
use crate::*;
create_desktop_container!({node_name} {struct});
impl_desktop_container!(TopLevelWidget {node_name} {struct});""")
                    top_level_mod_file.write(mod)
                else:
                    output_file = open(
                        f"{CONTAINERS_OUTPUT_DIR}/{node_name}.rs", 'w')
                    output_file.write(f"""{doc_comment}
use crate::*;
create_desktop_container!({node_name} {struct});
impl_desktop_container!(ContainerWidget {node_name} {struct});""")
                    container_mod_file.write(mod)
            else:
                output_file = open(f"{WIDGETS_OUTPUT_DIR}/{node_name}.rs", 'w')
                output_file.write(f"""{doc_comment}
use crate::*;
create_widget!({node_name} {struct});
impl_widget!({node_name} {struct});""")
                widgets_mod_file.write(mod)


async def main():
    # delete old binds
    for path in [BASE_OUTPUT_DIR, TOP_LEVEL_WIDGETS_OUTPUT_DIR, CONTAINERS_OUTPUT_DIR, WIDGETS_OUTPUT_DIR]:
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.mkdir(path)
    # scrap structs from gtk-rs docs.rs page
    req = requests.get(BASE_URL)
    html = BeautifulSoup(req.text, 'html.parser')
    prev_h2 = html.select_one("#structs")
    table = prev_h2.find_next_sibling('table')
    # mod files
    top_level_mod_file = open(f'{TOP_LEVEL_WIDGETS_OUTPUT_DIR}/mod.rs', 'w')
    container_mod_file = open(f'{CONTAINERS_OUTPUT_DIR}/mod.rs', 'w')
    widgets_mod_file = open(f'{WIDGETS_OUTPUT_DIR}/mod.rs', 'w')
    # generate bindings for all structs
    tasks = [scrap(tr, top_level_mod_file, container_mod_file,
                   widgets_mod_file) for tr in table.children]
    await asyncio.wait(tasks)


# run main
asyncio.run(main())
