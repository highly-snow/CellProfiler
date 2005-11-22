function handles = CreateWebPage(handles)

% Help for the CreateWebPage module:
% Category: Other
%
% SHORT DESCRIPTION:
% Creates the html for a webpage to display images, including a link
% to a zipped file with all of the included images.
% *************************************************************************
%
% This module will create an html file that will display the specified
% images and also produce a zip-file of these images with a link. The
% thumbnail images must be in the same directory as the original images.

% CellProfiler is distributed under the GNU General Public License.
% See the accompanying file LICENSE for details.
%
% Developed by the Whitehead Institute for Biomedical Research.
% Copyright 2003,2004,2005.
%
% Authors:
%   Anne Carpenter
%   Thouis Jones
%   In Han Kang
%   Ola Friman
%   Steve Lowe
%   Joo Han Chang
%   Colin Clarke
%   Mike Lamprecht
%   Susan Ma
%   Wyman Li
%
% Website: http://www.cellprofiler.org
%
% $Revision$

%%% Reads the current module number, because this is needed to find the
%%% variable values that the user entered.
[CurrentModule, CurrentModuleNum, ModuleName] = CPwhichmodule(handles);

%%%%%%%%%%%%%%%%%
%%% VARIABLES %%%
%%%%%%%%%%%%%%%%%

%textVAR01 = What did you call the full-size images you want to include?
%infotypeVAR01 = imagegroup
OrigImage = char(handles.Settings.VariableValues{CurrentModuleNum,1});
%inputtypeVAR01 = popupmenu

%textVAR02 = What did you call the thumbnail images you want to use to link to full images?
%choiceVAR02 = Do not use
%infotypeVAR02 = imagegroup
ThumbImage = char(handles.Settings.VariableValues{CurrentModuleNum,2});
%inputtypeVAR02 = popupmenu

%textVAR03 = Create HTML file before processing all images or after processing all images?
%choiceVAR03 = Before
%choiceVAR03 = After
CreateBA = char(handles.Settings.VariableValues{CurrentModuleNum,3});
%inputtypeVAR03 = popupmenu

%textVAR04 = What do you want to call the HTML file with the images above?
FileName = char(handles.Settings.VariableValues{CurrentModuleNum,4});
%defaultVAR04 = images1.html

%textVAR05 = HTML file save directory
%choiceVAR05 = One level over the images
%choiceVAR05 = Same as the images
DirectoryOption = char(handles.Settings.VariableValues{CurrentModuleNum,5});
%inputtypeVAR05 = popupmenu

%textVAR06 = Webpage title
PageTitle = char(handles.Settings.VariableValues{CurrentModuleNum,6});
%defaultVAR06 = CellProfiler Images

%textVAR07 = Choose the background color, or provide the html color code (e.g. #00FF00)
%choiceVAR07 = Black
%choiceVAR07 = White
%choiceVAR07 = Aqua
%choiceVAR07 = Blue
%choiceVAR07 = Fuchsia
%choiceVAR07 = Green
%choiceVAR07 = Gray
%choiceVAR07 = Lime
%choiceVAR07 = Maroon
%choiceVAR07 = Navy
%choiceVAR07 = Olive
%choiceVAR07 = Purple
%choiceVAR07 = Red
%choiceVAR07 = Silver
%choiceVAR07 = Teal
%choiceVAR07 = Yellow
BGColor = char(handles.Settings.VariableValues{CurrentModuleNum,7});
%inputtypeVAR07 = popupmenu custom

%textVAR08 = Number of columns for images
%choiceVAR08 = 1
%choiceVAR08 = 2
%choiceVAR08 = 3
%choiceVAR08 = 4
%choiceVAR08 = 5
ThumbCols = str2double(char(handles.Settings.VariableValues{CurrentModuleNum,8}));
%inputtypeVAR08 = popupmenu custom

%textVAR09 = Table border width (pixels)
%choiceVAR09 = 0
%choiceVAR09 = 1
%choiceVAR09 = 2
TableBorderWidth = char(handles.Settings.VariableValues{CurrentModuleNum,9});
%inputtypeVAR09 = popupmenu custom

%textVAR10 = Choose the table border color, or provide the html color code (e.g. #00FF00)
%choiceVAR10 = Black
%choiceVAR10 = White
%choiceVAR10 = Aqua
%choiceVAR10 = Blue
%choiceVAR10 = Fuchsia
%choiceVAR10 = Green
%choiceVAR10 = Gray
%choiceVAR10 = Lime
%choiceVAR10 = Maroon
%choiceVAR10 = Navy
%choiceVAR10 = Olive
%choiceVAR10 = Purple
%choiceVAR10 = Red
%choiceVAR10 = Silver
%choiceVAR10 = Teal
%choiceVAR10 = Yellow
TableBorderColor = char(handles.Settings.VariableValues{CurrentModuleNum,10});
%inputtypeVAR10 = popupmenu custom

%textVAR11 = Spacing between images (pixels)
%choiceVAR11 = 0
%choiceVAR11 = 1
%choiceVAR11 = 2
ThumbSpacing = char(handles.Settings.VariableValues{CurrentModuleNum,11});
%inputtypeVAR11 = popupmenu custom

%textVAR12 = Image border width (pixels)
%choiceVAR12 = 0
%choiceVAR12 = 1
%choiceVAR12 = 2
ThumbBorderWidth = char(handles.Settings.VariableValues{CurrentModuleNum,12});
%inputtypeVAR12 = popupmenu custom

%textVAR13 = Create new window for each click on thumbnail
%choiceVAR13 = Once only
%choiceVAR13 = For each image
%choiceVAR13 = No
CreateNewWindow = char(handles.Settings.VariableValues{CurrentModuleNum,13});
%inputtypeVAR13 = popupmenu

%textVAR14 = Specify a filename to create a ZIP file containing all full size images and link at the end of webpage for download. The '.zip' file extension will be added automatically.
%choiceVAR14 = Do not use
ZipFileName = char(handles.Settings.VariableValues{CurrentModuleNum,14});
%inputtypeVAR14 = popupmenu custom

%%%VariableRevisionNumber = 1

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% PRELIMINARY CALCULATIONS %%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
drawnow

%%% Determines which cycle is being analyzed.
SetBeingAnalyzed = handles.Current.SetBeingAnalyzed;
NumberOfImageSets = handles.Current.NumberOfImageSets;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% FIRST cycle FILE HANDLING %%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
drawnow

if ((SetBeingAnalyzed == 1) && strcmp(CreateBA,'Before')) || ((SetBeingAnalyzed == NumberOfImageSets) && strcmp(CreateBA,'After'))
    NumOrigImage = numel(handles.Pipeline.(['FileList' OrigImage]));
    if ~strcmp(ThumbImage,'Do not use')
        NumThumbImage = numel(handles.Pipeline.(['FileList' ThumbImage]));
        if NumOrigImage ~= NumThumbImage
            error(['Image processing was canceled in the ', ModuleName, ' module because the number of original images and thumbnail images do not match']);
        end
        ThumbImageFileNames = handles.Pipeline.(['FileList' ThumbImage]);
        ThumbImagePathName = handles.Pipeline.(['Pathname' ThumbImage]);
    end

    try
        OrigImageFileNames = handles.Pipeline.(['FileList' OrigImage]);
        OrigImagePathName = handles.Pipeline.(['Pathname' OrigImage]);
        ZipImagePathName = OrigImagePathName;
    catch error(['Image processing was canceled in the ', ModuleName, ' module because there was an error finding your images. You must specify images directly loaded by the LoadImages module.']);
    end

    CurrentImage = 1;

    if strcmp(DirectoryOption,'One level over the images')
        LastDirPos = max(findstr('\',OrigImagePathName))+1;
        if isempty(LastDirPos)
            LastDirPos = max(findstr('/',OrigImagePathName))+1;
        end

        HTMLSavePath = OrigImagePathName(1:LastDirPos-2);
        OrigImagePathName = OrigImagePathName(LastDirPos:end);
        try
            ThumbImagePathName = ThumbImagePathName(LastDirPos:end);
        catch
            error(['Image processing was canceled in the ', ModuleName, ' module because the folder ', ThumbImagePathName,' could not be found in the module ',ModuleName,'.']);
        end
    else
        HTMLSavePath = OrigImagePathName;
        OrigImagePathName = '';
        ThumbImagePathName = '';
    end

    WindowName = '_CPNewWindow';

    ZipList = {[]};

    Lines = '<HTML>';
    Lines = strvcat(Lines,['<HEAD><TITLE>',PageTitle,'</TITLE></HEAD>']);
    Lines = strvcat(Lines,['<BODY BGCOLOR=',AddQ(BGColor),'>']);
    Lines = strvcat(Lines,['<CENTER><TABLE BORDER=',TableBorderWidth, ' BORDERCOLOR=', AddQ(TableBorderColor), ' CELLPADDING=0',' CELLSPACING=',ThumbSpacing,'>']);
    %%% Creates the html to create a link to download the images as a
    %%% zipped archive.
    if ~strcmp(ZipFileName,'Do not use')
        Lines = strvcat(Lines,['<CENTER><A HREF = ',AddQ([ZipFileName,'.zip']),'>Download all images as a zipped file</A></CENTER>']);
    end
    while CurrentImage <= NumOrigImage
        Lines = strvcat(Lines,'<TR>');
        for i=1:ThumbCols

            Lines = strvcat(Lines,'<TD>');

            if ~strcmp(ThumbImage,'Do not use')
                if strcmp(CreateNewWindow,'Once only')
                    Lines = strvcat(Lines,['<A HREF=',AddQ(fullfile(OrigImagePathName,OrigImageFileNames{CurrentImage})),' TARGET=',AddQ(WindowName),'>']);
                elseif strcmp(CreateNewWindow,'For each image')
                    Lines = strvcat(Lines,['<A HREF=',AddQ(fullfile(OrigImagePathName,OrigImageFileNames{CurrentImage})),' TARGET=',AddQ([WindowName,num2str(CurrentImage)]),'>']);
                else
                    Lines = strvcat(Lines,['<A HREF=',AddQ(fullfile(OrigImagePathName,OrigImageFileNames{CurrentImage})),'>']);
                end
                Lines = strvcat(Lines,['<IMG SRC=',AddQ(fullfile(ThumbImagePathName,ThumbImageFileNames{CurrentImage})),' BORDER=',ThumbBorderWidth,'>']);
                Lines = strvcat(Lines,'</A>');
            else
                Lines = strvcat(Lines,['<IMG SRC=',AddQ(fullfile(OrigImagePathName,OrigImageFileNames{CurrentImage})),' BORDER=',ThumbBorderWidth,'>']);
            end

            Lines = strvcat(Lines,'</TD>');
            if ~strcmp(ZipFileName,'Do not use')
                ZipList(CurrentImage) = {fullfile(ZipImagePathName,OrigImageFileNames{CurrentImage})};
            end

            CurrentImage = CurrentImage + 1;
            if CurrentImage > NumOrigImage
                break;
            end

        end
        Lines = strvcat(Lines,'</TR>');
    end
    %%% Creates the zip file of all the high resolution images.
    if ~strcmp(ZipFileName,'Do not use')
        zip(fullfile(HTMLSavePath,ZipFileName),ZipList);
    end

    Lines = strvcat(Lines,'</TABLE></CENTER>');

    Lines = strvcat(Lines,'</BODY>');
    Lines = strvcat(Lines,'</HTML>');
    HTMLFullfile = fullfile(HTMLSavePath,FileName);
    dlmwrite(HTMLFullfile,Lines,'delimiter','');
    CPmsgbox(['Your webpage has been saved as ', HTMLFullfile, '.']);
    if SetBeingAnalyzed == 1
        %%% This is the first cycle, so this is the first time seeing this
        %%% module.  It should cause a cancel so no further processing is done
        %%% on this machine.
        set(handles.timertexthandle,'string','Cancel');
    end
end

%%%%%%%%%%%%%%%%%%%%%%%
%%% DISPLAY RESULTS %%%
%%%%%%%%%%%%%%%%%%%%%%%
drawnow

%%% The figure window display is unnecessary for this module, so the figure
%%% window is closed.
%%% Determines the figure number.
fieldname = ['FigureNumberForModule',CurrentModule];
ThisModuleFigureNumber = handles.Current.(fieldname);
%%% Closes the window if it is open.
if any(findobj == ThisModuleFigureNumber)
    close(ThisModuleFigureNumber)
end
drawnow

function AfterQuotation = AddQ(BeforeQuotation)
AfterQuotation = ['"',BeforeQuotation,'"'];