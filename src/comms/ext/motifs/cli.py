'''
comMS motif discovery extension: CLI wiring
'''

# -- Import external dependencies
import typer

# -- Instantiate Typer class as extMotifs 
extMotif = typer.Typer(add_completion=False)

# -- register_command: function required to register extension CLI with comMS
def register_command(root: typer.Typer):
    root.add_typer(extMotif, name='motif', help='Discover protein motifs and test for enrichment in treatments/fractions', rich_help_panel='Extensions')

# -- discover: add CLI wiring for motif discover command
@extMotif.command(rich_help_panel='Motif Commands')
def discover():
    '''
    De novo motif discovery
    '''
    pass

# -- label: add CLI wiring for motif label command
@extMotif.command(rich_help_panel='Motif Commands')
def label():
    '''
    Label motif occurences in proteins
    '''
    pass

# -- classify: add CLI wiring for motif classify command
@extMotif.command(rich_help_panel='Motif Commands')
def classify():
    '''
    Search for occurences of a specified motif class
    '''
    pass

# -- enrichment: add CLI wiring for motif enrichment command
@extMotif.command(rich_help_panel='Motif Commands')
def enrichment():
    '''
    Test motifs for differential enrichment
    '''
    pass