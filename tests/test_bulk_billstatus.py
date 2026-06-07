"""Unit tests for congress_sdk.bulk.billstatus XML parser."""

from __future__ import annotations

import pytest

from congress_sdk.bulk.billstatus import parse_billstatus_xml, _elem_to_val
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Minimal fixture XML — representative of real BILLSTATUS schema
# ---------------------------------------------------------------------------

_SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<billStatus>
  <version>3.0.0</version>
  <bill>
    <number>42</number>
    <updateDate>2024-05-01T12:00:00Z</updateDate>
    <originChamber>House</originChamber>
    <originChamberCode>H</originChamberCode>
    <type>HR</type>
    <introducedDate>2023-01-10</introducedDate>
    <congress>118</congress>
    <title>A test bill for unit testing</title>

    <policyArea>
      <name>Education</name>
    </policyArea>

    <subjects>
      <legislativeSubjects>
        <item>
          <name>Higher education</name>
          <updateDate>2023-01-15T00:00:00Z</updateDate>
        </item>
        <item>
          <name>Student aid</name>
          <updateDate>2023-01-15T00:00:00Z</updateDate>
        </item>
      </legislativeSubjects>
    </subjects>

    <sponsors>
      <item>
        <bioguideId>A000001</bioguideId>
        <fullName>Rep. Alice Example [D-CA-1]</fullName>
        <firstName>Alice</firstName>
        <lastName>Example</lastName>
        <party>D</party>
        <state>CA</state>
        <district>1</district>
        <isByRequest>N</isByRequest>
      </item>
    </sponsors>

    <cosponsors>
      <count>2</count>
      <countIncludingWithdrawnCosponsors>2</countIncludingWithdrawnCosponsors>
      <item>
        <bioguideId>B000002</bioguideId>
        <fullName>Rep. Bob Sample [R-TX-5]</fullName>
        <firstName>Bob</firstName>
        <lastName>Sample</lastName>
        <party>R</party>
        <state>TX</state>
        <district>5</district>
        <sponsorshipDate>2023-02-01</sponsorshipDate>
        <isOriginalCosponsor>True</isOriginalCosponsor>
      </item>
      <item>
        <bioguideId>C000003</bioguideId>
        <fullName>Rep. Carol Demo [D-NY-10]</fullName>
        <firstName>Carol</firstName>
        <lastName>Demo</lastName>
        <party>D</party>
        <state>NY</state>
        <district>10</district>
        <sponsorshipDate>2023-02-15</sponsorshipDate>
        <isOriginalCosponsor>False</isOriginalCosponsor>
      </item>
    </cosponsors>

    <committees>
      <item>
        <systemCode>hsed00</systemCode>
        <name>Education and the Workforce Committee</name>
        <chamber>House</chamber>
        <type>Standing</type>
        <activities>
          <item>
            <name>Referred To</name>
            <date>2023-01-10T00:00:00Z</date>
          </item>
        </activities>
      </item>
    </committees>

    <actions>
      <count>3</count>
      <item>
        <actionDate>2023-01-10</actionDate>
        <text>Introduced in House</text>
        <type>IntroReferral</type>
        <actionCode>Intro-H</actionCode>
        <sourceSystem>
          <code>9</code>
          <name>Library of Congress</name>
        </sourceSystem>
      </item>
      <item>
        <actionDate>2023-01-10</actionDate>
        <text>Referred to the Committee on Education and the Workforce.</text>
        <type>IntroReferral</type>
        <actionCode>H11100</actionCode>
        <sourceSystem>
          <code>2</code>
          <name>House floor actions</name>
        </sourceSystem>
      </item>
      <item>
        <actionDate>2023-03-15</actionDate>
        <text>Markup by committee.</text>
        <type>Committee</type>
        <sourceSystem>
          <code>1</code>
          <name>House committee actions</name>
        </sourceSystem>
      </item>
    </actions>

    <latestAction>
      <actionDate>2023-03-15</actionDate>
      <text>Markup by committee.</text>
    </latestAction>

    <titles>
      <item>
        <titleType>Display Title</titleType>
        <title>A test bill for unit testing</title>
        <updateDate>2024-01-01T00:00:00Z</updateDate>
      </item>
      <item>
        <titleType>Short Title(s) as Introduced</titleType>
        <title>Test Education Act</title>
        <updateDate>2024-01-01T00:00:00Z</updateDate>
        <billTextVersionName>Introduced in House</billTextVersionName>
        <billTextVersionCode>IH</billTextVersionCode>
      </item>
    </titles>

    <summaries>
      <summary>
        <versionCode>00</versionCode>
        <actionDate>2023-01-10</actionDate>
        <actionDesc>Introduced in House</actionDesc>
        <updateDate>2023-05-01T00:00:00Z</updateDate>
        <cdata>
          <text><p>This bill does important things for education.</p></text>
        </cdata>
      </summary>
    </summaries>

    <textVersions>
      <count>1</count>
      <item>
        <type>Introduced in House</type>
        <date>2023-01-10T04:00:00Z</date>
        <formats>
          <item>
            <url>https://www.govinfo.gov/content/pkg/BILLS-118hr42ih/xml/BILLS-118hr42ih.xml</url>
          </item>
        </formats>
      </item>
    </textVersions>

    <relatedBills>
      <item>
        <title>Related Education Act</title>
        <congress>118</congress>
        <number>100</number>
        <type>S</type>
        <latestAction>
          <actionDate>2023-02-01</actionDate>
          <text>Read twice and referred to committee.</text>
        </latestAction>
        <relationshipDetails>
          <item>
            <type>Related bill</type>
            <identifiedBy>CRS</identifiedBy>
          </item>
        </relationshipDetails>
      </item>
    </relatedBills>

    <cboCostEstimates />

    <laws />

    <amendments>
      <amendment>
        <number>1</number>
        <congress>118</congress>
        <type>HAMDT</type>
        <description>A test amendment.</description>
        <updateDate>2023-04-01T00:00:00Z</updateDate>
        <latestAction>
          <actionDate>2023-03-20</actionDate>
          <text>Agreed to by voice vote.</text>
        </latestAction>
      </amendment>
    </amendments>

  </bill>
</billStatus>
"""

_EMPTY_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<billStatus>
  <version>3.0.0</version>
  <bill>
    <number>1</number>
    <type>HR</type>
    <congress>119</congress>
    <title>Empty bill</title>
  </bill>
</billStatus>
"""


# ---------------------------------------------------------------------------
# Tests: parse_billstatus_xml
# ---------------------------------------------------------------------------


def test_parse_returns_dict():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    assert isinstance(bill, dict)


def test_top_level_scalar_fields():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    assert bill["number"] == "42"
    assert bill["type"] == "HR"
    assert bill["congress"] == "118"
    assert bill["originChamber"] == "House"
    assert bill["introducedDate"] == "2023-01-10"
    assert bill["title"] == "A test bill for unit testing"


def test_canonical_id_computed():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    assert bill["id"] == "bill:118:hr:42"


def test_source_tag():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    assert bill["_source"] == "govinfo_bulk"


def test_policy_area():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    assert isinstance(bill["policyArea"], dict)
    assert bill["policyArea"]["name"] == "Education"


def test_sponsors_list():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    sponsors = bill["sponsors"]
    assert isinstance(sponsors, list)
    assert len(sponsors) == 1
    s = sponsors[0]
    assert s["bioguideId"] == "A000001"
    assert s["party"] == "D"
    assert s["state"] == "CA"


def test_cosponsors_list():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    cosponsors = bill["cosponsors"]
    assert isinstance(cosponsors, list)
    assert len(cosponsors) == 2
    assert cosponsors[0]["bioguideId"] == "B000002"
    assert cosponsors[1]["bioguideId"] == "C000003"


def test_committees_list():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    committees = bill["committees"]
    assert isinstance(committees, list)
    assert len(committees) == 1
    c = committees[0]
    assert c["systemCode"] == "hsed00"
    assert c["chamber"] == "House"
    # Nested activities
    assert isinstance(c["activities"], list)
    assert c["activities"][0]["name"] == "Referred To"


def test_actions_list():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    actions = bill["actions"]
    assert isinstance(actions, list)
    assert len(actions) == 3
    assert actions[0]["actionDate"] == "2023-01-10"
    assert actions[0]["type"] == "IntroReferral"


def test_latest_action():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    la = bill["latestAction"]
    assert isinstance(la, dict)
    assert la["actionDate"] == "2023-03-15"
    assert "committee" in la["text"].lower()


def test_titles_list():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    titles = bill["titles"]
    assert isinstance(titles, list)
    assert len(titles) == 2
    title_types = {t["titleType"] for t in titles}
    assert "Display Title" in title_types


def test_summaries_list():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    summaries = bill["summaries"]
    assert isinstance(summaries, list)
    s = summaries[0]
    assert s["versionCode"] == "00"
    # Summary text is extracted from nested <cdata><text>
    cdata = s.get("cdata", {})
    assert isinstance(cdata, dict)
    text_val = cdata.get("text")
    assert text_val is not None
    assert "education" in text_val.lower()


def test_text_versions():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    tvs = bill["textVersions"]
    assert isinstance(tvs, list)
    assert len(tvs) == 1
    tv = tvs[0]
    assert tv["type"] == "Introduced in House"
    formats = tv["formats"]
    assert isinstance(formats, list)
    assert "govinfo.gov" in formats[0]["url"]


def test_related_bills():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    rbs = bill["relatedBills"]
    assert isinstance(rbs, list)
    rb = rbs[0]
    assert rb["type"] == "S"
    assert rb["number"] == "100"


def test_amendments_list():
    bill = parse_billstatus_xml(_SAMPLE_XML)
    amds = bill["amendments"]
    assert isinstance(amds, list)
    assert len(amds) == 1
    a = amds[0]
    assert a["type"] == "HAMDT"
    assert a["number"] == "1"


def test_empty_elements_omitted():
    # <cboCostEstimates /> and <laws /> should be None or absent
    bill = parse_billstatus_xml(_SAMPLE_XML)
    assert bill.get("cboCostEstimates") is None or bill.get("cboCostEstimates") == []
    assert bill.get("laws") is None or bill.get("laws") == []


def test_bytes_input():
    """Parser should accept bytes as well as str."""
    bill = parse_billstatus_xml(_SAMPLE_XML.encode("utf-8"))
    assert bill["number"] == "42"


def test_minimal_xml():
    """Minimal valid XML should not crash and produce an id."""
    bill = parse_billstatus_xml(_EMPTY_XML)
    assert bill["id"] == "bill:119:hr:1"


def test_missing_bill_element_raises():
    bad_xml = "<billStatus><version>3.0.0</version></billStatus>"
    with pytest.raises(ValueError, match="No <bill>"):
        parse_billstatus_xml(bad_xml)


# ---------------------------------------------------------------------------
# Tests: _elem_to_val (internal helpers)
# ---------------------------------------------------------------------------


def test_leaf_returns_text():
    elem = ET.fromstring("<foo>hello</foo>")
    assert _elem_to_val(elem) == "hello"


def test_leaf_empty_returns_none():
    elem = ET.fromstring("<foo/>")
    assert _elem_to_val(elem) is None


def test_item_children_returns_list():
    xml = "<sponsors><item><a>1</a></item><item><a>2</a></item></sponsors>"
    elem = ET.fromstring(xml)
    result = _elem_to_val(elem)
    assert isinstance(result, list)
    assert len(result) == 2


def test_count_sibling_discarded():
    xml = "<cosponsors><count>1</count><item><id>X</id></item></cosponsors>"
    elem = ET.fromstring(xml)
    result = _elem_to_val(elem)
    # count is discarded; only the item is returned
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["id"] == "X"


def test_same_tag_children_returns_list():
    xml = "<amendments><amendment><n>1</n></amendment><amendment><n>2</n></amendment></amendments>"
    elem = ET.fromstring(xml)
    result = _elem_to_val(elem)
    assert isinstance(result, list)
    assert len(result) == 2


def test_mixed_children_returns_dict():
    xml = "<latestAction><actionDate>2023-01-01</actionDate><text>Intro</text></latestAction>"
    elem = ET.fromstring(xml)
    result = _elem_to_val(elem)
    assert isinstance(result, dict)
    assert result["actionDate"] == "2023-01-01"
    assert result["text"] == "Intro"


def test_flatten_tag_joins_html():
    xml = "<text><p>First para.</p><p>Second para.</p></text>"
    elem = ET.fromstring(xml)
    result = _elem_to_val(elem)
    assert isinstance(result, str)
    assert "First para." in result
    assert "Second para." in result
