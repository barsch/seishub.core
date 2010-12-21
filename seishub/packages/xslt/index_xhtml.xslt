<?xml version="1.0" encoding="utf-8"?>

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xlink="http://www.w3.org/1999/xlink" exclude-result-prefixes="xlink" version="1.0">

    <xsl:output method="xml" encoding="utf-8" indent="yes" media-type="text/html"
        doctype-public="-//W3C//DTD XHTML 1.0 Strict//EN"
        doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"
        omit-xml-declaration="yes"/>

    <xsl:template match="/seishub">
        <html lang="en" xml:lang="en">
            <head>
                <title/>
                <link rel="stylesheet" type="text/css"
                      href="http://www.seishub.org/css/components.css"/>
            </head>
            <body>
                <h1>Indexes</h1>
                <table>
                    <tr>
                        <th>Key</th>
                        <th>Value(s)</th>
                    </tr>
                    <xsl:for-each select="*">
                        <xsl:sort select="name()" />
                        <tr>
                            <td><xsl:value-of select="name()"/></td>
                            <td>
                                <xsl:for-each select="value">
                                    <xsl:value-of select="text()"/><br />
                                </xsl:for-each>
                            </td>
                        </tr>
                    </xsl:for-each>
                </table>
            </body>
        </html>
    </xsl:template>

</xsl:stylesheet>
