from google.cloud import datastore

import logging
import re

from scispacy.umls_linking import UmlsEntityLinker
from scispacy.abbreviation import AbbreviationDetector


def loadModel(model):
    """
    Loading Named Entity Recognition model.
    Args:
        model: options: en_core_sci_sm, en_core_sci_lg, en_ner_bionlp13cg_md

    Returns:
        nlp: loaded model
    """
    # Load the model
    nlp = model.load()

    # Add pipe features to pipeline
    linker = UmlsEntityLinker(resolve_abbreviations=True)
    nlp.add_pipe(linker)

    # Add the abbreviation pipe to the spacy pipeline.
    abbreviation_pipe = AbbreviationDetector(nlp)
    nlp.add_pipe(abbreviation_pipe)
    logging.info("Model and add-ons successfully loaded.")
    return nlp


def extractMedEntities(vectorized_doc):
    """
    Returns UMLS entities contained in a text.
    Args:
        vectorized_doc:

    Returns:
        UMLS_tuis_entity: dict - key: entity and value: TUI code
    """
    # Pattern for TUI code
    pattern = 'T(\d{3})'

    UMLS_tuis_entity = {}
    entity_dict = {}

    linker = UmlsEntityLinker(resolve_abbreviations=True)

    for idx in range(len(vectorized_doc.ents)):
        entity = vectorized_doc.ents[idx]
        entity_dict[entity] = ''
        for umls_ent in entity._.umls_ents:
            entity_dict[entity] = linker.umls.cui_to_entity[umls_ent[0]]

        # RegEx expression if contains TUI code
        tui = re.search(pattern, str(entity_dict[entity]))
        if tui:
            UMLS_tuis_entity[str(entity)] = tui.group()
        else:
            UMLS_tuis_entity[str(entity)] = None

    return UMLS_tuis_entity


def addTask(datastore_client, doc_title, entities_dict):
    """
    Upload entities to Datastore.
    Args:
        datastore_client:
        doc_title:
        entities_dict:

    Returns:
        Datastore key object.
    """
    key = datastore_client.key('case', doc_title)
    task = datastore.Entity(key=key)
    task.update(
        entities_dict
    )
    datastore_client.put(task)
    # Then get by key for this entity
    logging.info("Uploaded {} to Datastore.".format(doc_title))
    return datastore_client.get(key)


def getCases(datastore_client, filter_dict, limit=10):
    """
    Get results of query with custom filters
    Args:
        datastore_client: Client object
        filter_dict: dict - e.g {parameter_A: [entity_name_A, entity_name_B],
                                parameter_B: [entitiy_name_C]
                                }
        limit: int - result limits per default 10
    Returns:
        results: list - query results
    """
    query = datastore_client.query(kind='case')

    for key, values in filter_dict.items():
        for value in values:
            query.add_filter(key, '=', value)
    results = list(query.fetch(limit=limit))
    return results
