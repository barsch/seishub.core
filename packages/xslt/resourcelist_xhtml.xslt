<?xml version="1.0" encoding="utf-8"?>

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xlink="http://www.w3.org/1999/xlink" exclude-result-prefixes="xlink"
    version="1.0">
    
    <xsl:output method="xml" encoding="utf-8" indent="yes"
        media-type="application/xhtml+xml" 
        doctype-public="-//W3C//DTD XHTML 1.0 Strict//EN"
        doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"
        omit-xml-declaration="yes" />
    
    <xsl:template match="/seishub/*">
        <tr>
            <td>
                <span>
                    <xsl:attribute name="class">
                        <xsl:text>icon icon-</xsl:text>
                        <xsl:value-of select="name()" />
                    </xsl:attribute>
                </span>
            </td>
            <td>
                <a>
                    <xsl:attribute name="href">
                        <xsl:value-of select="@xlink:href" />
                        <xsl:text>?format=xhtml</xsl:text>
                    </xsl:attribute>
                    <xsl:value-of select="." />
                </a>
            </td>
            <td>
                <xsl:value-of select="@xlink:href" />
            </td>
        </tr>
    </xsl:template>
    
    <xsl:template match="/seishub">
        <html>
            <head>
                <meta http-equiv="Content-Type" 
                      content="application/xhtml+xml; charset=UTF-8" />
                <link rel="stylesheet" type="text/css"
                      href="http://www.seishub.org/css/components.css" />
            </head>
            <body>
                <h1>
                    <xsl:value-of select="@xml:base" />
                </h1>
                <p>
                    <a href="?format=xml">[XML]</a>
                    <xsl:text> </xsl:text>
                    <a href="?format=json">[JSON]</a>
                </p>
                <table>
                    <tr>
                        <th></th>
                        <th>Name</th>
                        <th>Path</th>
                    </tr>
                    <tr>
                        <td></td>
                        <td><a href="..?format=xhtml">..</a></td>
                        <td></td>
                    </tr>
                    <xsl:apply-templates />
                </table>
            </body>
        </html>
    </xsl:template>

</xsl:stylesheet>