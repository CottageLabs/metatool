import plugin as plugin
from copy import deepcopy

validators = plugin.load_validators()
comparators = plugin.load_comparators()
generators = plugin.load_generators()

def validate_field(datatype, value, **validation_options):
    results = []
    for name, validator in validators.iteritems():
        if validator.supports(datatype, **validation_options):
            result = validator.validate(datatype, value, **validation_options)
            result.provenance = name
            results.append(result)
    return results

def validate_fieldset(fieldset, **validation_options):
    # first task is to validate all the individual fields, which may
    # also obtain from us some data to cross-reference
    for field in fieldset.fields():
        datatype = fieldset.datatype(field)
        for value in fieldset.values(field):
            results = validate_field(datatype, value, **validation_options)
            fieldset.results(field, value, results)

    # see if there's any crossreferencing we can do
    crossref_data = fieldset.get_crossref_data()
    if len(crossref_data) == 0:
        return
    
    # cross reference each field where possible
    for field in fieldset.fields():
        crossref = fieldset.crossref(field)
        
        # prune out all the comparator plugins that don't apply
        comparator_plugins = {}
        for name, comparator in comparators.iteritems():
            if comparator.supports(crossref):
                comparator_plugins[name] = comparator
        if len(comparator_plugins.keys()) == 0:
            continue
        
        additionals = {}
        field_comparison_register = {}
        for cr in crossref_data:
            compare = cr.get(crossref)
            additional = _list_compare(field_comparison_register, crossref, fieldset.values(field), compare, comparator_plugins, cr, **validation_options)
            for a in additional:
                _append(additionals, a, cr.source_name())
        
        if len(field_comparison_register.keys()) > 0: 
            fieldset.comparisons(field, field_comparison_register)
        
        if len(additionals.keys()) > 0:
            fieldset.additionals(field, additionals)
    

def _list_compare(comparison_register, datatype, original, compare, comparator_plugins, data_source, **comparison_options):
    additional = deepcopy(compare)
    for o in original:
        for c in compare:
            for name, p in comparator_plugins.iteritems():
                result = p.compare(datatype, o, c, **comparison_options)
                result.compared_with = c
                result.comparator = name
                result.data_source = data_source.source_name()
                if result.success:
                    _append(comparison_register, o, result)
                    if o in additional:
                        additional.remove(o)
                        
        # if we don't get any successful hits, record a blank result for the value
        if o not in comparison_register:
            comparison_register[o] = []
            
    return additional

def _append(d, k, v):
    if k in d:
        d[k].append(v)
    else:
        d[k] = [v]                

def validate_model(modeltype, model_stream, **validation_options):
    fieldsets = None
    for name, genny in generators.iteritems():
        if genny.supports(modeltype, **validation_options):
            fieldsets = genny.generate(modeltype, model_stream, **validation_options)
            break
    
    for fieldset in fieldsets:
        validate_fieldset(fieldset, **validation_options)
    
    return fieldsets


def fieldsets_to_html(fieldsets):
    frag = ""
    i = 1
    for fieldset in fieldsets:
        frag += "<h2>Fieldset " + str(i) + "</h2>"
        i += 1
        frag += fieldset_to_html(fieldset)
    return frag

def fieldset_to_html(fieldset):
    entries = _fieldset_to_result_entries(fieldset)
    
    tables = []
    for entry in entries:
        tables.append(_result_entry_to_table(entry))
    
    return "\n\n".join(tables)

def _result_entry_to_table(entry):
    frag = "<table border='1'>"
    
    # header row
    header = entry[0]
    frag += "<thead><tr>"
    frag += "<td class='field'>" + header[0] + "</td>"
    frag += "<td class='value'>" + header[1] + "</td>"
    frag += "<td class='datatype'> datatype: " + header[2] + "</td>"
    frag += "<td class='crossref'> cross-reference as: " + header[3] + "</td>"
    frag += "</tr></thead><tbody>"
    
    # success row
    success = entry[1]
    success_message = ("Successfully Validated" if success[0] == "pass" 
                        else "Validated with Warnings" if success[0] == "pass_warn" 
                        else "Failed to Validate" if success[0] == "fail" 
                        else "Field not Validated")
    
    cr_frag = ""
    if success[1] == False:
        cr_frag = "<p class='successful_crossref_none'>Field was not cross-referenced against an external source</p>"
    elif len(success[1]) == 0:
        cr_frag = "<p class='successful_crossref_fail'>Field was cross-referenced against external sources, but could not be validated.</p>"
    else:
        cr_frag = "<p class='successful_crossref_title'>Successfully cross-referenced with</p>"
        for cw, prov in success[1]:
            cr_frag += "<p><span class='successful_crossref_entry'>" + cw + "</span><span class='successful_crossref_prov'> - " + prov + "</span></p>"
    
    frag += "<tr>"
    frag += "<td colspan='2' class='overall_success " + success[0] + "'>" + success_message + "</td>"
    frag += "<td colspan='2' class='successful_crossref'>" + cr_frag + "</td>"
    frag += "</tr>"
    
    # corrections and alternatives
    ca_row = entry[2]
    corr_frag = ""
    if len(ca_row[0]) == 0:
        corr_frag = "<p class='correction_none'>No proposed corrections</p>"
    else:
        corr_frag = "<p class='correction_title'>Proposed corrections</p>"
        corr_frag += "<ul>"
        for corr, prov in ca_row[0]:
            corr_frag += "<li><span class='correction_option'>" + corr + "</span><span class='correction_prov'> - " + prov + "</span></li>"
        corr_frag += "</ul>"
    
    alt_frag = ""
    if len(ca_row[1]) == 0:
        alt_frag = "<p class='alternatives_none'>No alternative suggestions for this field</p>"
    else:
        alt_frag = "<p class='alternatives_title'>Additional/Alternative values you may consider</p>"
        alt_frag += "<ul>"
        for alt, prov in ca_row[1]:
            alt_frag += "<li><span class='alternative_option'>" + alt + "</span><span class='alternative_prov'> - " + prov + "</span></li>"
        alt_frag += "</ul>"
    
    frag += "<tr>"
    frag += "<td colspan='2' class='corrections'>" + corr_frag + "</td>"
    frag += "<td colspan='2' class='alternatives'>" + alt_frag + "</td>"
    frag += "</tr>"
    
    # info, warn, error
    iwe = entry[3]
    if len(iwe[0]) == 0 and len(iwe[1]) == 0 and len(iwe[2]) == 0:
        frag += "<tr><td colspan='4' class='messages'><p class='no_messages'>No messages associated with this field/value</p></td></tr>"
    else:
        frag += "<tr><td colspan='4' class='messages'><p class='messages_title'>Messages</p><ul>"
        for info, prov in iwe[0]:
            frag += "<li class='info'><span class='info_message'>INFO: " + info + "</span><span class='info_prov'> - " + prov + "</span></li>"
        for warn, prov in iwe[1]:
            frag += "<li class='warn'><span class='warn_message'>WARN: " + warn + "</span><span class='warn_prov'> - " + prov + "</span></li>"
        for error, prov in iwe[2]:
            frag += "<li class='error'><span class='error_message'>ERROR: " + error + "</span><span class='error_prov'> - " + prov + "</span></li>"
        frag += "</ul></td></tr>"
    
    frag += "</tbody></table>"
    return frag

def _fieldset_to_result_entries(fieldset):
    entries = []
    for field in fieldset.fields():
        for value in fieldset.values(field):
            
            # create a header row
            header_row = [field, value, fieldset.datatype(field), fieldset.crossref(field)]
            
            validations = fieldset.get_validations(field, value)
            comparisons = fieldset.get_comparisons(field, value)
            
            # obtain all of the corrections and alternatives
            corrections = []
            alternatives = []
            for v in validations:
                cs = v.get_corrections()
                prov = v.provenance
                for c in cs:
                    corrections.append((c, prov))
                alts = v.get_alternatives()
                for a in alts:
                    alternatives.append((a, prov))
            if comparisons is not None:
                for co in comparisons:
                    cs = co.get_corrections()
                    prov = co.data_source
                    for c in cs:
                        corrections.append((c, prov))
            
            # now write the corrections and alternatives row    
            ca_row = [corrections, alternatives]
            
            # now get the info, warn and error messages
            info = []
            warn = []
            error = []
            for v in validations:
                ins = v.get_info()
                wrns = v.get_warn()
                errs = v.get_error()
                prov = v.provenance
                for i in ins:
                    info.append((i, prov))
                for w in wrns:
                    warn.append((w, prov))
                for e in errs:
                    error.append((e, prov))
            
            message_row = [info, warn, error]
            
            # calculate the overall validation success
            success = "unvalidated"
            if len(validations) > 0:
                success = "pass"
                if len(error) > 0:
                    success = "fail"
                elif len(warn) > 0:
                    success = "pass_warn"
            
            # look for successful cross-references to report on
            crossrefs = []
            if comparisons is not None:
                for co in comparisons:
                    crossrefs.append((co.compared_with, co.data_source))
            else:
                crossrefs = False
            
            success_row = [success, crossrefs]
            
            row_block = [header_row, success_row, ca_row, message_row]
            entries.append(row_block)
            
    return entries


































                            
                    
