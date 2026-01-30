%% mics.cls
%% LaTeX class for Midwest Instruction and Computing Symposium (MICS) papers
%% Based on MICS Paper Submission Guidelines

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{mics}[2026/01/30 MICS Paper Class]

% Base class
\LoadClass[12pt,letterpaper]{article}

% Required packages
\RequirePackage[letterpaper,left=1.25in,right=1.25in,top=1in,bottom=1in]{geometry}
\RequirePackage{times}
\RequirePackage{setspace}
\RequirePackage{titlesec}
\RequirePackage{ragged2e}
\RequirePackage{caption}
\RequirePackage{fancyhdr}

% Single spacing
\singlespacing

% No paragraph indentation, blank line between paragraphs
\setlength{\parindent}{0pt}
\setlength{\parskip}{12pt}

% Justification (left and right)
\justifying

% Title formatting
% Support for multiple authors side-by-side
\newcommand{\authorblock}[1]{%
    \begin{minipage}[t]{0.45\textwidth}%
    \centering%
    #1%
    \end{minipage}%
}

\renewcommand{\maketitle}{%
    \thispagestyle{empty}%
    \begin{center}%
        \vspace*{0.5in}%
        {\fontsize{18}{22}\selectfont\bfseries\@title\par}%
        \vspace{24pt}%
        {\fontsize{14}{17}\selectfont\@author\par}%
        \vspace{24pt}%
    \end{center}%
}

% Abstract formatting
\renewcommand{\abstractname}{Abstract}
\renewenvironment{abstract}{%
    \begin{center}%
    {\fontsize{16}{19}\selectfont\bfseries\abstractname\par}%
    \end{center}%
    \vspace{12pt}%
    \fontsize{12}{14}\selectfont%
    \justifying%
}{%
    \par%
    \clearpage%
    \setcounter{page}{1}%
}

% Section formatting
% Level 1: left justify, bold, 16 point, 2 blank lines before, 1 blank line after
\titleformat{\section}
{\fontsize{16}{19}\selectfont\bfseries}
{\thesection}
{1em}
{}
\titlespacing*{\section}
{0pt}
{24pt}
{12pt}

% Level 2: left justify, bold, 14 point, 2 blank lines before, 1 blank line after
\titleformat{\subsection}
{\fontsize{14}{17}\selectfont\bfseries}
{\thesubsection}
{1em}
{}
\titlespacing*{\subsection}
{0pt}
{24pt}
{12pt}

% Level 3: left justify, bold, 12 point, 2 blank lines before, 1 blank line after
\titleformat{\subsubsection}
{\fontsize{12}{14}\selectfont\bfseries}
{\thesubsubsection}
{1em}
{}
\titlespacing*{\subsubsection}
{0pt}
{24pt}
{12pt}

% Page numbering - centered at bottom
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Table and Figure captions - centered
\captionsetup{
    justification=centering,
    labelsep=colon,
    font=normalsize
}

% References heading: bold, left justify, 16 point, 2 blank lines before, 1 blank line after
\renewcommand{\refname}{References}
\let\oldbibliography\bibliography
\renewcommand{\bibliography}[1]{%
    \clearpage
    \titleformat{\section}
    {\fontsize{16}{19}\selectfont\bfseries}
    {}{0em}{}
    \titlespacing*{\section}
    {0pt}
    {24pt}
    {12pt}
    \oldbibliography{#1}
}

% Alternatively, for thebibliography environment
\renewenvironment{thebibliography}[1]{%
    \section*{\refname}
    \list{\@biblabel{\@arabic\c@enumiv}}%
    {\settowidth\labelwidth{\@biblabel{#1}}%
    \leftmargin\labelwidth
    \advance\leftmargin\labelsep
    \@openbib@code
    \usecounter{enumiv}%
    \let\p@enumiv\@empty
    \renewcommand\theenumiv{\@arabic\c@enumiv}}%
    \sloppy
    \clubpenalty4000
    \@clubpenalty \clubpenalty
    \widowpenalty4000%
    \sfcode`\.\@m}
{\def\@noitemerr
{\@latex@warning{Empty `thebibliography' environment}}%
\endlist}

\endinput