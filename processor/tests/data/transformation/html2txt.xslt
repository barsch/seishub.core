<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output encoding="utf-8" indent="no" media-type="text/plain"
        method="text" />
    <xsl:template match="/html">
        <xsl:value-of select="head/title/text()" />
        <xsl:text>&#10;</xsl:text>
        <xsl:for-each select="body/table/tr">
            <xsl:value-of select="td/em/text()" />
            <xsl:for-each select="td">
                <xsl:if test="not(count(em))">
                    <xsl:text>,</xsl:text>
                    <xsl:value-of select="text()" />
                </xsl:if>
            </xsl:for-each>
            <xsl:text>&#10;</xsl:text>
        </xsl:for-each>
    </xsl:template>
</xsl:stylesheet>
