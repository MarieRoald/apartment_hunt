import sqlite3
from rich.table import Table
from rich.console import Console
from rich.markdown import Markdown


__author__ = "Marie Roald & Yngve Mardal Moe"


def print_table_from_cursor(cursor, console=None):
    """Format the output from a SQL query as a table and print it.
    """
    if console is None:
        console = Console()
    output_table = Table(show_header=True)

    for description in cursor.description:
        output_table.add_column(description[0])

    for row in cursor:
        output_table.add_row(*(str(element) for element in row))
    console.print(output_table)


console = Console()
with sqlite3.connect('boligdata.db') as connection:
    c = connection.cursor()

    display_columns = ["adresse","felleskost/mnd.", "totalpris", "primærrom", "bruksareal", "sykkeltid-uio", "sykkeltid-met"]
    display_columns_string =",".join([f'"{d}"' for d in display_columns])

    # Find the cheapest apartments
    console.print(Markdown("## The 10 cheapest apartments:"))
    query = f"""\
    SELECT {display_columns_string} 
    FROM boligdata 
    WHERE totalpris is not NULL 
    AND bruksareal >= 20
    ORDER BY totalpris 
    LIMIT 5
    """
    c.execute(query)
    console.print(f" Query: \n[i]{query}[/i] \n Result:")
    print_table_from_cursor(c, console=console)

    console.print("However, just because an apartment is cheap in total does not mean the price per square meter is good.")
    console.print(Markdown("## The 10 cheapest aparment (per m^2) within price range"))
    query = f"""\
    SELECT totalpris/bruksareal as kvadratmeterpris, {display_columns_string} 
    FROM boligdata 
    WHERE totalpris is not NULL 
    AND totalpris <= 4000000
    ORDER BY kvadratmeterpris 
    LIMIT 5
    """
    c.execute(query)
    
    console.print(f" Query: \n[i]{query}[/i] \n Result:")
    print_table_from_cursor(c, console=console)



    # Find apartments with balcony by selecting those with larger usable area compared
    # to primary area (bruksareal vs areal av primærrom).
    console.print(Markdown("## The 10 cheapest apartments with a balcony"))
    console.print(
        "We are also interested in apartments with a balcony. "
        "Unfortunately, this info is not easily accessible, but we found one heuristic "
        "that seemed to work well. "
        "We can filter appartments with a larger \"usable\" area than \"primary\" area "
        "(bruksareal og primærrom). Then, most apartments we find have a balcony."
    )
    query = f"""\
    SELECT {display_columns_string} 
    FROM boligdata
    WHERE totalpris is not NULL 
    AND primærrom < bruksareal
    ORDER BY totalpris 
    LIMIT 10
    """
    c.execute(query)
    console.print(f" Query: \n[i]{query}[/i] \n Result:")
    print_table_from_cursor(c, console=console)

    # The ten cheapest apartments with short commute for both of us
    console.print("And a short commute")
    console.print(Markdown("## The 10 cheapest apartments with a short commute to both UiO and OsloMet"))
    query = f"""
    SELECT {display_columns_string}, "kollektivtid-uio", "kollektivtid-met"
    FROM boligdata
    WHERE totalpris is not NULL 
    AND "sykkeltid-uio" < 20
    AND "sykkeltid-met" < 20
    AND "kollektivtid-uio" < 30
    AND "kollektivtid-met" < 30
    ORDER BY totalpris 
    LIMIT 10
    """
    c.execute(query)
    console.print(f" Query: \n[i]{query}[/i] \n Result:")
    print_table_from_cursor(c, console=console)

    # Some information about different regions in Oslo
    console.print(Markdown("## Information about the most expensive postal zones"))
    query = f"""
    SELECT
     postnummer,
     AVG(totalpris/bruksareal),
     AVG(totalpris),
     AVG(bruksareal),
     COUNT(totalpris)
    FROM boligdata 
    WHERE totalpris IS NOT NULL
    GROUP BY postnummer
    ORDER BY avg(totalpris/bruksareal) DESC
    """
    c.execute(query)
    console.print(f" Query: \n[i]{query}[/i] \n Result:")
    print_table_from_cursor(c, console=console)
