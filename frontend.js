const elt = document.getElementById('calculator');
const calculator = Desmos.GraphingCalculator(elt, {lockViewport: false, expressions: false, settingsMenu: false});
const blankState = calculator.getState();

const canvas = document.createElement("canvas");
const ctx = canvas.getContext("2d");

const renderVideo = () => {
    fetch('http://localhost:5000/renderFullVideo', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        executeFrameLoad(data);
    })
    .catch(error => {
        console.error('Error:', error);
        renderVideo();
    });
}


const init = () => {

}


const executeFrameLoad = (data) => {
    // console.log("data", data);
    document.getElementById("updateInfo").innerText = data["updateInfo"];
    if (data["isFinished"]) {
        return
    }
    data = data["image"]
    elt.style.width = (2000) + "px";
    elt.style.height = (Math.round(data['imgData']['height']/data['imgData']['width']*2000)) + "px";

    calculator.resize();
    
    calculator.setMathBounds({
        left: -0.1*data['imgData']['width'],
        right: 1.1*data['imgData']['width'],
        bottom: -0.1*data['imgData']['height'],
        top: 1.1*data['imgData']['height']
    });

    let state = calculator.getState();
    for (let i = 0; i < data['polygons'].length; i++) {
        state['expressions']['list'][i] = {type: "expression", id: "polygon" + (i + 1), latex: data['polygons'][i]['polygon'], color: data['polygons'][i]['color'], fillOpacity: "1", lines: false};
    }
    let bytes = (new Blob([JSON.stringify(state)]).size)
    // console.log("" + bytes + " bytes recorded - (" + (bytes/3500000 * 100) + "% of maximum)");

    calculator.setState(blankState);
    calculator.setState(state);

    calculator.asyncScreenshot(returnFrame);
}


const returnFrame = (frame) => {
    let image = new Image();
    image.src = frame;
    image.onload = () => {
        canvas.width = image.width;
        canvas.height = image.height;

        ctx.drawImage(image, 0, 0);

        fetch('http://localhost:5000/saveNewFrame', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }, 
        body: JSON.stringify({image: canvas.toDataURL('image/jpeg')})
        })
        .then(response => response.json())
        .then(data => {
            calculator.setBlank();
            renderVideo();
        })
        .catch(error => {
            console.error('Error:', error);
            returnFrame(frame);
        });
    }
}


const getSingleImage = () => {
    fetch('http://localhost:5000/getData', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        elt.style.width = (2000) + "px";
        elt.style.height = (Math.round(data['imgData']['height']/data['imgData']['width']*2000)) + "px";

        calculator.resize();
        
        calculator.setMathBounds({
            left: -0.1*data['imgData']['width'],
            right: 1.1*data['imgData']['width'],
            bottom: -0.1*data['imgData']['height'],
            top: 1.1*data['imgData']['height']
        });

        let state = calculator.getState();
        for (let i = 0; i < data['polygons'].length; i++) {
            state['expressions']['list'][i] = {type: "expression", id: "polygon" + (i + 1), latex: data['polygons'][i]['polygon'], color: data['polygons'][i]['color'], fillOpacity: "1", lines: false};
        }
        let bytes = (new Blob([JSON.stringify(state)]).size)
        // console.log("" + bytes + " bytes recorded - (" + (bytes/3500000 * 100) + "% of maximum)");

        calculator.setState(state);
    })
}

init();