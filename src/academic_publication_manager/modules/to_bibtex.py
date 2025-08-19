import bibtexparser

from academic_publication_manager.modules.production import bibtex_examples


def reorder_dict(d, priority_keys=None, en_alpha=False):
    """
    Reordena um dict colocando certas chaves primeiro
    e opcionalmente ordena as demais em ordem alfabética.

    Args:
        d (dict): O dicionário original.
        priority_keys (list): Lista de chaves que devem vir primeiro (se existirem).
        en_alpha (bool): Se True, ordena as outras chaves alfabeticamente.

    Returns:
        dict: Novo dicionário reordenado.
    """
    if priority_keys is None:
        priority_keys = []

    # Garante que só usemos chaves realmente existentes
    priority_keys = [k for k in priority_keys if k in d]

    # Define as demais chaves
    other_keys = [k for k in d if k not in priority_keys]

    if en_alpha:
        other_keys = sorted(other_keys)

    ordered_keys = priority_keys + other_keys

    return {k: d[k] for k in ordered_keys}
    
def bibtex_to_dicts(filepath: str) -> dict:
    with open(filepath, encoding="utf-8") as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)

    data = {}
    for entry in bib_database.entries:
        key = entry.pop("ID")
        entry["entry-type"] = entry.pop("ENTRYTYPE")
        
        entry = reorder_dict(entry, priority_keys=["entry-type","title","year"], en_alpha=True)
        
        for bibkey in bibtex_examples[entry["entry-type"]]:
            entry.setdefault(bibkey, "")
        
        data[key] = entry
    
    return data



def dict_entry_to_bibstring(entry: dict, key: str) -> str:
    """
    Converte apenas uma entrada do dicionário (works.json) para uma string em formato BibTeX.
    
    Args:
        entry (dict): Dicionário com chaves.
        key (str): Chave do item que será convertido.
    
    Returns:
        str: String em formato BibTeX da entrada escolhida.
    """

    entry["ID"] = key
    entry["ENTRYTYPE"] = entry.pop("entry-type")

    bib_db = bibtexparser.bibdatabase.BibDatabase()
    bib_db.entries = [entry]

    writer = bibtexparser.bwriter.BibTexWriter()
    writer.indent = "  "  # dois espaços
    writer.order_entries_by = ("ID",)  # opcional

    return writer.write(bib_db)

def id_list_to_bibtex_string(entry: dict, id_list: list) -> str:
    out = ""
    for ID_name in id_list:
        res = dict_entry_to_bibstring(entry[ID_name], citekey = ID_name)
        out += res + "\n\n"
    return out
