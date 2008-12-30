<?xml version="1.0" encoding="utf-8"?>

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xlink="http://www.w3.org/1999/xlink" exclude-result-prefixes="xlink" version="1.0">

    <xsl:output method="xml" encoding="utf-8" indent="yes" media-type="text/html"
        doctype-public="-//W3C//DTD XHTML 1.0 Strict//EN"
        doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"
        omit-xml-declaration="yes"/>

    <xsl:template match="/seishub/*">
        <tr>
            <td>
                <span>
                    <xsl:attribute name="class">
                        <xsl:text>icon icon-</xsl:text>
                        <xsl:value-of select="@category"/>
                    </xsl:attribute>
                </span>
            </td>
            <td>
                <a>
                    <xsl:attribute name="href">
                        <xsl:value-of select="@xlink:href"/>
                        <xsl:if test="name()='folder'">
                            <xsl:text>?format=xhtml</xsl:text>
                        </xsl:if>
                    </xsl:attribute>
                    <xsl:value-of select="."/>
                </a>
            </td>
            <td>
                <xsl:value-of select="@xlink:href"/>
            </td>
        </tr>
    </xsl:template>

    <xsl:template match="/seishub">
        <html lang="en" xml:lang="en">
            <head>
                <title/>
                <link rel="stylesheet" type="text/css"
                    href="http://www.seishub.org/css/components.css"/>
            </head>
            <body>
                <h1>
                    <a>
                        <xsl:attribute name="href">
                            <xsl:value-of select="@xml:base"/>
                            <xsl:text>?format=xhtml</xsl:text>
                        </xsl:attribute>
                        <xsl:value-of select="@xml:base"/>
                    </a>
                </h1>
                <p>
                    <xsl:text>Format: </xsl:text>
                    <a href="?">[XML]</a>
                    <xsl:text> </xsl:text>
                    <a href="?format=json">[JSON]</a>
                    <xsl:text> </xsl:text>
                    <a href="?format=admin">[ADMIN]</a>
                </p>
                <table>
                    <tr>
                        <th/>
                        <th>Name</th>
                        <th>Path</th>
                    </tr>
                    <tr>
                        <td/>
                        <td>
                            <a href="..?format=xhtml">..</a>
                        </td>
                        <td/>
                    </tr>
                    <xsl:apply-templates select="/seishub/folder"/>
                    <xsl:apply-templates select="/seishub/resource"/>
                </table>
            </body>
        </html>
    </xsl:template>

</xsl:stylesheet>
