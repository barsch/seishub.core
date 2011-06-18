<?xml version="1.0" encoding="utf-8"?>

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xlink="http://www.w3.org/1999/xlink" exclude-result-prefixes="xlink" version="1.0">

    <xsl:output method="text" encoding="utf-8" media-type="application/json"/>

    <xsl:template match="/seishub">
        <xsl:text>{</xsl:text>

        <xsl:text>"folder":[</xsl:text>
        <xsl:for-each select="*[@category='folder']">
            <xsl:text>"</xsl:text>
            <xsl:value-of select="@xlink:href"/>
            <xsl:text>"</xsl:text>
            <xsl:if test="not (position()=last())">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        <xsl:text>],</xsl:text>

        <xsl:text>"file":[</xsl:text>
        <xsl:for-each select="*[@category='file']">
            <xsl:text>"</xsl:text>
            <xsl:value-of select="@xlink:href"/>
            <xsl:text>"</xsl:text>
            <xsl:if test="not (position()=last())">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        <xsl:text>],</xsl:text>

        <xsl:text>"mapping":[</xsl:text>
        <xsl:for-each select="*[@category='mapping']">
            <xsl:text>"</xsl:text>
            <xsl:value-of select="@xlink:href"/>
            <xsl:text>"</xsl:text>
            <xsl:if test="not (position()=last())">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        <xsl:text>],</xsl:text>

        <xsl:text>"mapping-folder":[</xsl:text>
        <xsl:for-each select="*[@category='mapping-folder']">
            <xsl:text>"</xsl:text>
            <xsl:value-of select="@xlink:href"/>
            <xsl:text>"</xsl:text>
            <xsl:if test="not (position()=last())">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        <xsl:text>],</xsl:text>

        <xsl:text>"resource":[</xsl:text>
        <xsl:for-each select="*[@category='resource']">
            <xsl:text>"</xsl:text>
            <xsl:value-of select="@xlink:href"/>
            <xsl:text>"</xsl:text>
            <xsl:if test="not (position()=last())">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        <xsl:text>],</xsl:text>

        <xsl:text>"index":[</xsl:text>
        <xsl:for-each select="*[@category='index']">
            <xsl:text>"</xsl:text>
            <xsl:value-of select="."/>
            <xsl:text>"</xsl:text>
            <xsl:if test="not (position()=last())">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        <xsl:text>],</xsl:text>

        <xsl:text>"alias":[</xsl:text>
        <xsl:for-each select="*[@category='alias']">
            <xsl:text>"</xsl:text>
            <xsl:value-of select="@xlink:href"/>
            <xsl:text>"</xsl:text>
            <xsl:if test="not (position()=last())">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        <xsl:text>],</xsl:text>

        <xsl:text>"xmlroot":[</xsl:text>
        <xsl:for-each select="*[@category='xmlroot']">
            <xsl:text>"</xsl:text>
            <xsl:value-of select="@xlink:href"/>
            <xsl:text>"</xsl:text>
            <xsl:if test="not (position()=last())">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        <xsl:text>],</xsl:text>

        <xsl:text>"package":[</xsl:text>
        <xsl:for-each select="*[@category='package']">
            <xsl:text>"</xsl:text>
            <xsl:value-of select="@xlink:href"/>
            <xsl:text>"</xsl:text>
            <xsl:if test="not (position()=last())">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        <xsl:text>],</xsl:text>

        <xsl:text>"resourcetype":[</xsl:text>
        <xsl:for-each select="*[@category='resourcetype']">
            <xsl:text>"</xsl:text>
            <xsl:value-of select="@xlink:href"/>
            <xsl:text>"</xsl:text>
            <xsl:if test="not (position()=last())">
                <xsl:text>,</xsl:text>
            </xsl:if>
        </xsl:for-each>
        <xsl:text>]</xsl:text>

        <xsl:text>}</xsl:text>
    </xsl:template>

</xsl:stylesheet>
