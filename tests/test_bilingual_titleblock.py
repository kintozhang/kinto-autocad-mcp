import pytest
from src.autocad.bilingual_titleblock import profile, validate_values, build_expression


def valid():
    return {f['tag']:('NTS' if f['tag']=='SCALE' else 'TEST') for f in profile()['fields']}


def test_values_are_exact_and_escape_lisp():
    values=valid();values['PROJECT']='Test "quoted"'
    code=build_expression(values,'622')
    assert '\\"quoted\\"' in code
    assert '(cons 2 "SHEET")' in code


def test_missing_field_rejected():
    values=valid();del values['SHEET']
    with pytest.raises(ValueError):validate_values(values)


def test_long_field_rejected():
    values=valid();values['REV']='a'*100
    with pytest.raises(ValueError):validate_values(values)


def test_control_character_rejected():
    values=valid();values['TITLE']='Bad\nTitle'
    with pytest.raises(ValueError):validate_values(values)


def test_fit_scale_must_be_nts():
    values=valid();values['SCALE']='1:1'
    with pytest.raises(ValueError):validate_values(values)
