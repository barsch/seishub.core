<?xml version="1.0" encoding="utf-8"?>

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xlink="http://www.w3.org/1999/xlink" exclude-result-prefixes="xlink"
  version="1.0">

  <xsl:output method="text" encoding="utf-8" media-type="application/json" />

  <xsl:template match="/seishub/*">
    <xsl:text>"</xsl:text>
    <xsl:value-of select="name()" />
    <xsl:text>":["</xsl:text>
    <xsl:value-of select="text()" />
    <xsl:text>"],</xsl:text>
  </xsl:template>
  
  <xsl:template match="/seishub">
    <xsl:text>{</xsl:text>
    <xsl:apply-templates select="/seishub/*"/>
    <xsl:text>}</xsl:text>
  </xsl:template>

</xsl:stylesheet>
