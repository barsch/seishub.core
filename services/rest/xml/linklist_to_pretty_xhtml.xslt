<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    exclude-result-prefixes="xlink" version="1.0">
    <xsl:output method="html" />

    <xsl:template match="*[@xlink:type = 'simple' and @xlink:href]">
        <li>
            <a href="{@xlink:href}">
                <xsl:apply-templates />
            </a>
        </li>
    </xsl:template>

    <xsl:template match="seishub">
        <html>
            <body>
                <ul>
                    <xsl:apply-templates />
                </ul>
            </body>
        </html>
    </xsl:template>

</xsl:stylesheet>