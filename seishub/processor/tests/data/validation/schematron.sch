<?xml version="1.0" encoding="utf-8"?>

<schema xmlns="http://www.ascc.net/xml/schematron">
    <pattern name="Sum equals 100%.">
        <rule context="Total">
            <assert test="sum(//Percent)=100">Sum is not 100%.</assert>
        </rule>
    </pattern>
</schema>
