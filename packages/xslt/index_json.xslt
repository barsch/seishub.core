<?xml version="1.0" encoding="utf-8"?>

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xlink="http://www.w3.org/1999/xlink" exclude-result-prefixes="xlink"
  version="1.0">

  <xsl:output method="text" encoding="utf-8" media-type="application/json" />

  <xsl:template match="/seishub">
    <xsl:text>{</xsl:text>

    <xsl:for-each select="*">
      <xsl:sort select="name()" />
      <xsl:text>"</xsl:text>
      <xsl:value-of select="name()" />
      <xsl:text>":[</xsl:text>

      <xsl:for-each select="value">
        <xsl:text>"</xsl:text>
        <xsl:value-of select="text()" />
        <xsl:text>",</xsl:text>
      </xsl:for-each>

      <xsl:text>],</xsl:text>
    </xsl:for-each>

    <xsl:text>}</xsl:text>
  </xsl:template>

</xsl:stylesheet>
