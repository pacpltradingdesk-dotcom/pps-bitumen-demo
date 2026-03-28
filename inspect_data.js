const XLSX = require('xlsx');

const filePath = "C:\\Users\\HP\\Desktop\\Sales VG30 Dashboard all india prising.xlsx";

try {
    console.log("Reading Excel headers...");
    // Read only the first 10 rows to be fast
    const workbook = XLSX.readFile(filePath, { sheetRows: 10 });
    const firstSheetName = workbook.SheetNames[0];
    const worksheet = workbook.Sheets[firstSheetName];

    // Convert to JSON to see headers
    const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

    if (jsonData.length > 0) {
        console.log("\nHeaders found:");
        console.log(jsonData[0]);
        console.log("\nSample Row 1:");
        console.log(jsonData[1]);
    } else {
        console.log("No data found in the first sheet.");
    }
} catch (error) {
    console.error("Error reading file:", error.message);
}
