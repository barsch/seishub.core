<?xml version="1.0" encoding="utf-8"?>

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    xmlns:xlink="http://www.w3.org/1999/xlink" exclude-result-prefixes="xlink"
    version="1.0">
    
    <xsl:output method="text" encoding="utf-8"
        media-type="application/json" />
    
    <xsl:template match="/seishub">
        <xsl:text>{</xsl:text>

            <xsl:if test="//folder">
                <xsl:text>"folder":[</xsl:text>
                <xsl:for-each select="//folder">
                    <xsl:text>"</xsl:text>
                    <xsl:value-of select="@xlink:href" />
                    <xsl:text>"</xsl:text>
                    <xsl:if test="not (position()=last())">
                        <xsl:text>,</xsl:text>
                    </xsl:if>
                </xsl:for-each>
                <xsl:text>],</xsl:text>
            </xsl:if>

            <xsl:if test="//resource">
                <xsl:text>"resource":[</xsl:text>
                <xsl:for-each select="//resource">
                    <xsl:text>"</xsl:text>
                    <xsl:value-of select="@xlink:href" />
                    <xsl:text>"</xsl:text>
                    <xsl:if test="not (position()=last())">
                        <xsl:text>,</xsl:text>
                    </xsl:if>
                </xsl:for-each>
                <xsl:text>],</xsl:text>
            </xsl:if>

        <xsl:text>}</xsl:text>
    </xsl:template>

</xsl:stylesheet>