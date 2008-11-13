<?xml version="1.0" encoding="utf-8"?>

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    xmlns:xlink="http://www.w3.org/1999/xlink" exclude-result-prefixes="xlink"
    version="1.0">
    
    <xsl:output method="text" encoding="utf-8"
        media-type="application/json" />
    
    <xsl:template match="/seishub">
        <xsl:text>{</xsl:text>

            <xsl:if test="//package">
                <xsl:text>"package":[</xsl:text>
                <xsl:for-each select="//package">
                    <xsl:text>"</xsl:text>
                    <xsl:value-of select="@xlink:href" />
                    <xsl:text>"</xsl:text>
                    <xsl:if test="not (position()=last())">
                        <xsl:text>,</xsl:text>
                    </xsl:if>
                </xsl:for-each>
                <xsl:text>],</xsl:text>
            </xsl:if>

            <xsl:if test="//resourcetype">
                <xsl:text>"resourcetype":[</xsl:text>
                <xsl:for-each select="//resourcetype">
                    <xsl:text>"</xsl:text>
                    <xsl:value-of select="@xlink:href" />
                    <xsl:text>"</xsl:text>
                    <xsl:if test="not (position()=last())">
                        <xsl:text>,</xsl:text>
                    </xsl:if>
                </xsl:for-each>
                <xsl:text>],</xsl:text>
            </xsl:if>

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

            <xsl:if test="//mapping">
                <xsl:text>"mapping":[</xsl:text>
                <xsl:for-each select="//mapping">
                    <xsl:text>"</xsl:text>
                    <xsl:value-of select="@xlink:href" />
                    <xsl:text>"</xsl:text>
                    <xsl:if test="not (position()=last())">
                        <xsl:text>,</xsl:text>
                    </xsl:if>
                </xsl:for-each>
                <xsl:text>],</xsl:text>
            </xsl:if>

            <xsl:if test="//alias">
                <xsl:text>"alias":[</xsl:text>
                <xsl:for-each select="//alias">
                    <xsl:text>"</xsl:text>
                    <xsl:value-of select="@xlink:href" />
                    <xsl:text>"</xsl:text>
                    <xsl:if test="not (position()=last())">
                        <xsl:text>,</xsl:text>
                    </xsl:if>
                </xsl:for-each>
                <xsl:text>],</xsl:text>
            </xsl:if>

            <xsl:if test="//index">
                <xsl:text>"index":[</xsl:text>
                <xsl:for-each select="//index">
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