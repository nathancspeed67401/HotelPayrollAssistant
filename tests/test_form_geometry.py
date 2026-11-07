"""Check printed-grid registration against independently placed clock-cell marks."""
import numpy as np
import cv2
from PIL import Image, ImageDraw
import pytest
from app.form_geometry import find_form_grid


def make_marked_form():
    image = Image.new('RGB', (958, 1350), 'white')
    draw = ImageDraw.Draw(image)
    columns = [213, 345, 478, 607, 745]
    weeks = [[362+39*i for i in range(8)],
             [674, 713, 751, 789, 827, 865, 903, 941]]
    colors = {}
    for week, boundaries in enumerate(weeks):
        for x in columns:
            draw.line((x, boundaries[0], x, boundaries[-1]), fill='#777777', width=2)
        for y in boundaries:
            draw.line((75, y, 919, y), fill='#777777', width=2)
        for day in range(7):
            row = week*7+day
            for column in range(4):
                color = (30+row*9, 40+column*40, 240)
                colors[row, column] = color
                # A mark close to the left boundary catches clipped first digits.
                x, y = columns[column]+8, (boundaries[day]+boundaries[day+1])//2
                draw.ellipse((x-5, y-5, x+5, y+5), fill=color)
    return image, colors


@pytest.mark.parametrize('distortion', ['none', 'perspective', 'rotate'])
def test_all_clock_cells_keep_their_own_edge_marks(distortion):
    image, colors = make_marked_form()
    if distortion == 'perspective':
        source = np.float32([[0,0],[957,0],[957,1349],[0,1349]])
        target = np.float32([[28,0],[957,12],[916,1349],[0,1331]])
        image = Image.fromarray(cv2.warpPerspective(np.asarray(image),
            cv2.getPerspectiveTransform(source,target), image.size,
            borderValue=(255,255,255)))
    elif distortion == 'rotate':
        image = image.rotate(1.2, resample=Image.Resampling.BICUBIC, fillcolor='white')
    grid = find_form_grid(image)
    assert grid is not None
    for (row, column), color in colors.items():
        crop = np.asarray(grid.crop_cell(image,row,column)).astype('int16')
        matches = np.max(np.abs(crop-np.asarray(color)),axis=2) < 8
        assert matches.sum() >= 35, (distortion,row,column)


def test_registration_abstains_when_printed_grid_is_missing():
    assert find_form_grid(Image.new('RGB',(958,1350),'white')) is None


def test_registration_rejects_wrong_column_spacing():
    image = Image.new('RGB',(958,1350),'white')
    draw = ImageDraw.Draw(image)
    for x in [213,250,478,607,745]:
        draw.line((x,350,x,950),fill='black',width=2)
    for y in range(362,950,39):
        draw.line((75,y,919,y),fill='black',width=2)
    assert find_form_grid(image) is None


def test_grid_cannot_be_reused_for_a_different_image_size():
    image,_ = make_marked_form()
    grid = find_form_grid(image)
    assert grid is not None
    with pytest.raises(ValueError,match='different image size'):
        grid.crop_cell(image.resize((479,675)),0,0)
