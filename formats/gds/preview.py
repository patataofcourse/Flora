"""
This module (eventually) contains a small GDS simulator, suitable for piecing together a visually
explorable representation of room layouts, a structured view of dialogue events, and an overview
of the script's logical control flow.

TODO: WIP, and no priority at the moment
"""

from .model import GDSProgram

def preview_room(prog: GDSProgram):
    """
    Executes the provided room script, by building the room in a small view window
    like the game itself would, but with many introspection tools.
    
    The program should consist of
    1.  a main view in which the content visible on the bottom screen is assembled.
        All items placed here should be represented by their actual animated sprites in game,
        and bounding boxes should be shown. Clicking on an item should show technical details,
        such as exactly what type of item it is, or in the case of triggers, what event they cause.
        This information also includes the conditions under which the object is included in the scene.
    2.  a topscreen view displaying what map information is being set by the room script, and possibly
        other adhoc sprites like the objectives arrows. Again, bounding boxes where relevant.
    3.  a sidebar that lists all items placed in the room by category, also split by what conditions need
        to be required to make the item appear.
    
    This information could all just be an informational display, but optionally, certain properties like the
    positions, names and events of items could be editable. A "save" functionality should write the result of
    these edits to a new GDA script.
    """
    pass

def preview_event(prog: GDSProgram):
    """
    Executes the provided event script, by playing through the sequence in a small view window
    like the game itself would, but with many introspection tools.
    
    The program should consist of
    1.  a main view in which actors and text bubbles are displayed like in the game.
        Items placed here should be represented by their actual animated sprites in game,
        and clickable bounding boxes shown to display technical details of placement and animation logic.
    2.  (optionally, depending on what the event can do) a topscreen view displaying the results of special
        logic displaying information on the top screen.
    3.  a sidebar listing all events in the dialogue tree in order, highlighting the currently displayed step,
        allowing the user to click on previous ones to rewind. Should also display the logic instructions
        determining which parts of the event are played, but allow the user to override them and see
        all parts of the dialogue.
    
    This information could all just be an informational display, but optionally, certain properties like the
    positions, count and animations of the actors, as well as the dialogue text, could be editable. A "save"
    functionality should write the result of these edits to a new GDA script.
    """
    pass

def preview_puzzle(prog: GDSProgram):
    """
    Least likely to actually get done: executes the provided puzzle script. These seldom have much interactivity,
    but they're extremely contextual on the engine used.
    
    The program should consist of
    1.  a main view displaying the assembled touchscreen view a player would be presented with in-game,
        with animations and bounding boxes for important elements (and grid line hints where applicable).
    2.  a "topscreen view" which may not need to be completely accurate, instead listing all crucial information
        about the puzzle such as title, description, picarat counts, even the hints in a separate tab.
    3.  a sidebar with debug information about the internal state of the puzzle engine, and the ability
        to show/hide technical objects used for puzzle grading that would otherwise clutter the screen.
    
    Of course this view is highly dependent on the puzzle engine, which makes it difficult to conceptualize at this point.
    """