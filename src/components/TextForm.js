import React, { useState } from 'react';

export default function TextForm(props) {
  const [text, setText] = useState('');

  const handleUpper = () => {
    let newText = text.toUpperCase();
    setText(newText);
    props.showAlert("text converted to uppercase","success")
  };

  const handleLower = () => {
    let newText = text.toLowerCase();
    setText(newText);
    props.showAlert("text converted to lowercase","success")

  };

  const handleClear = () => {
    setText('');
    props.showAlert("text cleared","success")

  };

  const handleCopy = () => {
    let textArea = document.getElementById('textArea');
    textArea.select();
    navigator.clipboard.writeText(textArea.value);
    props.showAlert("text copied to clipboard","success")

  };

  const handleTrim = () => {
    let newText = text.trim();
    setText(newText);
    props.showAlert("excess spaces trimmed","success")

  };

  const handleOnChange = (event) => {
    setText(event.target.value);
  };

  return (
    <>
      <div className="container" style={{ color: props.mode === 'dark' ? 'white' : 'black' }}>
        <h2>{props.heading}</h2>
        <div className="mb-3">
          <textarea
            className="form-control"
            value={text}
            onChange={handleOnChange}
            style={{
              backgroundColor: props.mode === 'dark' ? '#3a3b3c' : 'white',
              color: props.mode === 'dark' ? 'white' : 'black',
            }}
            id="textArea"
            rows="8"
          ></textarea>
        </div>
        <button className="btn btn-primary mx-1 my-1" onClick={handleUpper}>
          Convert to Uppercase
        </button>
        <button className="btn btn-primary mx-1 my-1" onClick={handleLower}>
          Convert to Lowercase
        </button>
        <button className="btn btn-primary mx-1 my-1" onClick={handleClear}>
          Clear Text
        </button>
        <button className="btn btn-primary mx-1 my-1" onClick={handleTrim}>
          Remove Extra Spaces
        </button>
        <button className="btn btn-primary mx-1 my-1" onClick={handleCopy}>
          Copy Text
        </button>

        <h3 className="my-3">Your text summary</h3>
        <p>
          {text.split(/\s+/).filter((element) => element.length !== 0).length} words and {text.length} characters
        </p>
        <p>{0.008 * text.split(/\s+/).filter((element) => element.length !== 0).length} Minutes read</p>

        <h3 className="my-3">Preview</h3>
        <p>{text.length > 0 ? text : 'Enter something in the textbox above to preview it here'}</p>
      </div>
    </>
  );
}
