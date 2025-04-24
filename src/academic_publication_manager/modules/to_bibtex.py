import bibtexparser

def bibtex_to_dicts(bibtex_string: str) -> dict:
    bib_database = bibtexparser.loads(bibtex_string)
    result = {}

    pub_field_by_type = {
        "article": "journal",
        "phdthesis": "school",
        "mastersthesis": "school",
        "inproceedings": "booktitle",
        "techreport": "institution",
        "book": "publisher",
        "manual": "organization",
    }

    for entry in bib_database.entries:
        entry_type = entry.get("ENTRYTYPE", "misc").lower()
        entry_key = entry.get("ID", "unknown")

        # Autores
        authors = entry.get("author", "")
        authors_list = [a.strip() for a in authors.split(" and ")] if authors else []

        # Título e subtítulo
        full_title = entry.get("title", "").strip()
        if ": " in full_title:
            title, subtitle = full_title.split(": ", 1)
        elif " – " in full_title:
            title, subtitle = full_title.split(" – ", 1)
        else:
            title, subtitle = full_title, ""

        # Publicador
        pub_field = pub_field_by_type.get(entry_type, None)
        publicator_name = entry.get(pub_field, "") if pub_field else ""

        # Serial numbers
        serial_numbers = []
        for k in ["isbn", "issn", "doi"]:
            if k in entry:
                serial_numbers.append({"type": k, "value": entry[k].strip()})

        # Criar dicionário no seu formato
        result[entry_key] = {
            "type": entry_type,
            "title": title.strip(),
            "subtitle": subtitle.strip(),
            "authors": authors_list,
            "year": entry.get("year", "").strip(),
            "url": entry.get("url", "").strip(),
            "language": entry.get("language", "").strip(),
            "version": entry.get("edition", "").strip(),
            "publicator_name": publicator_name.strip(),
            "serial_numbers": serial_numbers
        }

    return result


def dict_to_bibtex(entry: dict, citekey: str = "ref") -> str:
    def is_valid(value):
        return isinstance(value, str) and value.strip() != ""

    entry_type = entry.get("type", "misc").lower()

    # Campos válidos por tipo
    field_map_by_type = {
        "article": {"author", "title", "journal", "year", "volume", "number", "pages", "month", "note", "issn", "doi", "url"},
        "book": {"author", "editor", "title", "publisher", "year", "volume", "series", "edition", "month", "note", "isbn", "url"},
        "inbook": {"author", "editor", "title", "chapter", "pages", "publisher", "year", "volume", "series", "type", "address", "edition", "month", "note", "isbn"},
        "incollection": {"author", "title", "booktitle", "publisher", "year", "editor", "pages", "organization", "series", "address", "edition", "month", "note", "isbn"},
        "inproceedings": {"author", "title", "booktitle", "year", "editor", "pages", "organization", "publisher", "address", "month", "note", "url"},
        "manual": {"title", "author", "organization", "address", "edition", "year", "month", "note", "url"},
        "mastersthesis": {"author", "title", "school", "year", "type", "address", "month", "note", "url"},
        "phdthesis": {"author", "title", "school", "year", "type", "address", "month", "note", "url"},
        "techreport": {"author", "title", "institution", "year", "type", "number", "address", "month", "note", "url"},
        "unpublished": {"author", "title", "note", "year", "month", "url"},
        "misc": {"author", "title", "howpublished", "month", "year", "note", "url"}
    }

    allowed_fields = field_map_by_type.get(entry_type, field_map_by_type["misc"])
    bibtex_fields = {}

    # Autores
    if "authors" in entry:
        authors = " and ".join(entry["authors"])
        if is_valid(authors):
            bibtex_fields["author"] = authors

    # Título com subtítulo, se houver
    if is_valid(entry.get("title")):
        title = entry["title"].strip()
        if is_valid(entry.get("subtitle")):
            title += ": " + entry["subtitle"].strip()
        bibtex_fields["title"] = title

    # Publication name → campo específico por tipo
    pub = entry.get("publicator_name", "")
    if is_valid(pub):
        if entry_type == "article":
            bibtex_fields["journal"] = pub
        elif entry_type in {"phdthesis", "mastersthesis"}:
            bibtex_fields["school"] = pub
        elif entry_type == "techreport":
            bibtex_fields["institution"] = pub
        elif entry_type == "inproceedings":
            bibtex_fields["booktitle"] = pub
        elif entry_type == "book":
            bibtex_fields["publisher"] = pub
        elif entry_type == "manual":
            bibtex_fields["organization"] = pub

    # Versão → edition
    if entry_type in {"book", "manual"} and is_valid(entry.get("version")):
        bibtex_fields["edition"] = entry["version"]

    if is_valid(entry.get("year")):
        bibtex_fields["year"] = entry["year"]

    if is_valid(entry.get("url")):
        bibtex_fields["url"] = entry["url"]

    if is_valid(entry.get("language")):
        bibtex_fields["language"] = entry["language"]

    # Serial numbers: isbn, issn, doi
    for sn in entry.get("serial_numbers", []):
        sn_type = sn.get("type", "").lower()
        sn_value = sn.get("value", "")
        if is_valid(sn_value):
            if sn_type in {"isbn", "issn", "doi"}:
                bibtex_fields[sn_type] = sn_value

    # Constrói a string final do BibTeX
    bibtex = f"@{entry_type}{{{citekey},\n"
    for key, val in bibtex_fields.items():
        if key in allowed_fields:
            bibtex += f"  {key} = {{{val}}},\n"
    bibtex = bibtex.rstrip(",\n") + "\n}"
    return bibtex + "\n"


def id_list_to_bibtex_string(entry: dict, id_list: list) -> str:
    out = ""
    for ID_name in id_list:
        res = dict_to_bibtex(entry[ID_name], citekey = ID_name)
        out += res + "\n"
    return out
