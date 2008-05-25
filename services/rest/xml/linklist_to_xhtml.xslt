<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    exclude-result-prefixes="xlink" version="1.0">
    <xsl:output method="html" />

    <xsl:template match="package[@xlink:type = 'simple' and @xlink:href]">
        <li class="package">
          <a href="{@xlink:href}">
            <xsl:apply-templates />
          </a>
        </li>
    </xsl:template>
    <xsl:template match="resourcetype[@xlink:type = 'simple' and @xlink:href]">
        <li class="resourcetype">
          <a href="{@xlink:href}">
            <xsl:apply-templates />
          </a>
        </li>
    </xsl:template>

    <xsl:template match="seishub">
        <html>
          <head>
            <style type="text/css">
              body {
                color: black;
                background-color: white;
                font-family: "trebuchet ms", verdana, helvetica, arial, sans-serif;
                font-size: 12pt;
                margin: 20px;
                padding: 0;
              }
              li.package {
                background: url('https://localhost:40443/images/package.gif');
                list-style-type: none;
                list-style-position: outside;
                background-repeat: no-repeat;
                padding-left: 20px;
                margin-left: 0px;
              }
              li.resourcetype {
                background: url('https://localhost:40443/images/resourcetype.gif');
                list-style-type: none;
                list-style-position: outside;
                background-repeat: no-repeat;
                padding-left: 20px;
                margin-left: 0px;
              }
            </style>
          </head>
          <body>
            <h1>SeisHub REST Browser</h1>
            [<a href="?format=application/xml">View this page as XML document</a>]
            <ul>
              <xsl:apply-templates />
            </ul>
          </body>
        </html>
    </xsl:template>

</xsl:stylesheet>